"""
Camada de acesso a dados: aqui mora todo o SQL.

A interface gráfica nunca escreve SQL — ela chama serviços, que chamam este
módulo. Isso mantém as telas simples e permite testar o sistema sem abrir a
janela (ver testes/test_core.py).
"""

from core.db import transacao

# --------------------------------------------------------------------------- #
# Funcionários
# --------------------------------------------------------------------------- #


def listar_funcionarios(apenas_ativos: bool = True) -> list:
    sql = "SELECT * FROM funcionarios"
    if apenas_ativos:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY nome COLLATE NOCASE"

    with transacao() as con:
        return con.execute(sql).fetchall()


def buscar_funcionario(funcionario_id: int):
    with transacao() as con:
        return con.execute(
            "SELECT * FROM funcionarios WHERE id = ?", (funcionario_id,)
        ).fetchone()


def criar_funcionario(nome: str, cargo: str = "Atendente") -> int:
    with transacao() as con:
        cursor = con.execute(
            "INSERT INTO funcionarios (nome, cargo) VALUES (?, ?)",
            (nome.strip(), cargo.strip() or "Atendente"),
        )
        return cursor.lastrowid


def atualizar_funcionario(funcionario_id: int, nome: str, cargo: str) -> None:
    with transacao() as con:
        con.execute(
            "UPDATE funcionarios SET nome = ?, cargo = ? WHERE id = ?",
            (nome.strip(), cargo.strip() or "Atendente", funcionario_id),
        )


def desativar_funcionario(funcionario_id: int) -> None:
    """Não apagamos: o histórico de vendas precisa continuar apontando para ele."""
    with transacao() as con:
        con.execute(
            "UPDATE funcionarios SET ativo = 0 WHERE id = ?", (funcionario_id,)
        )


# --------------------------------------------------------------------------- #
# Produtos
# --------------------------------------------------------------------------- #


def listar_produtos(termo: str = "", apenas_ativos: bool = True) -> list:
    sql = "SELECT * FROM produtos WHERE 1 = 1"
    parametros: list = []

    if apenas_ativos:
        sql += " AND ativo = 1"
    if termo.strip():
        sql += " AND (nome LIKE ? OR categoria LIKE ?)"
        curinga = f"%{termo.strip()}%"
        parametros += [curinga, curinga]

    sql += " ORDER BY categoria COLLATE NOCASE, nome COLLATE NOCASE"

    with transacao() as con:
        return con.execute(sql, parametros).fetchall()


def buscar_produto(produto_id: int):
    with transacao() as con:
        return con.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()


def criar_produto(nome: str, categoria: str, preco_centavos: int) -> int:
    with transacao() as con:
        cursor = con.execute(
            "INSERT INTO produtos (nome, categoria, preco_centavos) VALUES (?, ?, ?)",
            (nome.strip(), categoria.strip() or "Geral", int(preco_centavos)),
        )
        return cursor.lastrowid


def atualizar_produto(produto_id: int, nome: str, categoria: str, preco_centavos: int) -> None:
    with transacao() as con:
        con.execute(
            "UPDATE produtos SET nome = ?, categoria = ?, preco_centavos = ? WHERE id = ?",
            (nome.strip(), categoria.strip() or "Geral", int(preco_centavos), produto_id),
        )


def desativar_produto(produto_id: int) -> None:
    with transacao() as con:
        con.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))


def categorias() -> list:
    with transacao() as con:
        linhas = con.execute(
            "SELECT DISTINCT categoria FROM produtos ORDER BY categoria COLLATE NOCASE"
        ).fetchall()
    return [linha["categoria"] for linha in linhas]


# --------------------------------------------------------------------------- #
# Caixas
# --------------------------------------------------------------------------- #


def caixa_aberto():
    with transacao() as con:
        return con.execute(
            """
            SELECT c.*, f.nome AS operador_abertura
              FROM caixas c
              JOIN funcionarios f ON f.id = c.funcionario_abertura_id
             WHERE c.status = 'ABERTO'
            """
        ).fetchone()


def buscar_caixa(caixa_id: int):
    with transacao() as con:
        return con.execute(
            """
            SELECT c.*,
                   fa.nome AS operador_abertura,
                   ff.nome AS operador_fechamento
              FROM caixas c
              JOIN funcionarios fa ON fa.id = c.funcionario_abertura_id
         LEFT JOIN funcionarios ff ON ff.id = c.funcionario_fechamento_id
             WHERE c.id = ?
            """,
            (caixa_id,),
        ).fetchone()


def inserir_caixa(data_operacao, aberto_em, funcionario_id, valor_abertura_centavos) -> int:
    with transacao() as con:
        cursor = con.execute(
            """
            INSERT INTO caixas
                   (data_operacao, aberto_em, funcionario_abertura_id, valor_abertura_centavos)
            VALUES (?, ?, ?, ?)
            """,
            (data_operacao, aberto_em, funcionario_id, int(valor_abertura_centavos)),
        )
        return cursor.lastrowid


def marcar_caixa_fechado(
    caixa_id, fechado_em, funcionario_id, valor_contado_centavos,
    diferenca_centavos, observacoes,
) -> None:
    with transacao() as con:
        con.execute(
            """
            UPDATE caixas
               SET status = 'FECHADO',
                   fechado_em = ?,
                   funcionario_fechamento_id = ?,
                   valor_contado_centavos = ?,
                   diferenca_centavos = ?,
                   observacoes = ?
             WHERE id = ?
            """,
            (fechado_em, funcionario_id, int(valor_contado_centavos),
             int(diferenca_centavos), observacoes, caixa_id),
        )


def registrar_planilha(caixa_id: int, caminho: str) -> None:
    with transacao() as con:
        con.execute("UPDATE caixas SET planilha = ? WHERE id = ?", (str(caminho), caixa_id))


def listar_caixas(data_inicio: str = "", data_fim: str = "", apenas_fechados: bool = True) -> list:
    """Usado na tela de Histórico para consultar os dias já fechados."""
    sql = """
        SELECT c.*,
               fa.nome AS operador_abertura,
               ff.nome AS operador_fechamento,
               (SELECT COUNT(*)  FROM vendas v
                 WHERE v.caixa_id = c.id AND v.cancelada = 0)               AS qtd_vendas,
               (SELECT COALESCE(SUM(v.total_centavos), 0) FROM vendas v
                 WHERE v.caixa_id = c.id AND v.cancelada = 0)               AS total_centavos
          FROM caixas c
          JOIN funcionarios fa ON fa.id = c.funcionario_abertura_id
     LEFT JOIN funcionarios ff ON ff.id = c.funcionario_fechamento_id
         WHERE 1 = 1
    """
    parametros: list = []

    if apenas_fechados:
        sql += " AND c.status = 'FECHADO'"
    if data_inicio:
        sql += " AND c.data_operacao >= ?"
        parametros.append(data_inicio)
    if data_fim:
        sql += " AND c.data_operacao <= ?"
        parametros.append(data_fim)

    sql += " ORDER BY c.data_operacao DESC, c.id DESC"

    with transacao() as con:
        return con.execute(sql, parametros).fetchall()


# --------------------------------------------------------------------------- #
# Vendas
# --------------------------------------------------------------------------- #


def inserir_venda(caixa_id, funcionario_id, data_hora, forma_pagamento, total_centavos, itens) -> int:
    """
    Grava a venda e seus itens na MESMA transação.

    Se algum item falhar, nada é gravado — não fica venda sem item no banco.
    """
    with transacao() as con:
        cursor = con.execute(
            """
            INSERT INTO vendas (caixa_id, funcionario_id, data_hora, forma_pagamento, total_centavos)
            VALUES (?, ?, ?, ?, ?)
            """,
            (caixa_id, funcionario_id, data_hora, forma_pagamento, int(total_centavos)),
        )
        venda_id = cursor.lastrowid

        con.executemany(
            """
            INSERT INTO itens_venda
                   (venda_id, produto_id, nome_produto, categoria,
                    quantidade, preco_unit_centavos, subtotal_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    venda_id,
                    item.get("produto_id"),
                    item["nome"],
                    item.get("categoria", "Geral"),
                    int(item["quantidade"]),
                    int(item["preco_unit_centavos"]),
                    int(item["quantidade"]) * int(item["preco_unit_centavos"]),
                )
                for item in itens
            ],
        )
        return venda_id


def cancelar_venda(venda_id: int, cancelada_em: str, motivo: str) -> None:
    """Estorno lógico: a venda continua no banco, marcada como cancelada."""
    with transacao() as con:
        con.execute(
            """
            UPDATE vendas
               SET cancelada = 1, cancelada_em = ?, motivo_cancelamento = ?
             WHERE id = ? AND cancelada = 0
            """,
            (cancelada_em, motivo, venda_id),
        )


def listar_vendas(caixa_id: int, incluir_canceladas: bool = True) -> list:
    sql = """
        SELECT v.*, f.nome AS vendedor
          FROM vendas v
          JOIN funcionarios f ON f.id = v.funcionario_id
         WHERE v.caixa_id = ?
    """
    if not incluir_canceladas:
        sql += " AND v.cancelada = 0"
    sql += " ORDER BY v.data_hora, v.id"

    with transacao() as con:
        return con.execute(sql, (caixa_id,)).fetchall()


def listar_itens_do_caixa(caixa_id: int, incluir_canceladas: bool = False) -> list:
    """Linha a linha: cada produto vendido, com hora e vendedor."""
    sql = """
        SELECT v.id            AS venda_id,
               v.data_hora,
               v.forma_pagamento,
               v.cancelada,
               f.nome          AS vendedor,
               i.nome_produto,
               i.categoria,
               i.quantidade,
               i.preco_unit_centavos,
               i.subtotal_centavos
          FROM itens_venda i
          JOIN vendas v       ON v.id = i.venda_id
          JOIN funcionarios f ON f.id = v.funcionario_id
         WHERE v.caixa_id = ?
    """
    if not incluir_canceladas:
        sql += " AND v.cancelada = 0"
    sql += " ORDER BY v.data_hora, v.id, i.id"

    with transacao() as con:
        return con.execute(sql, (caixa_id,)).fetchall()


def itens_da_venda(venda_id: int) -> list:
    with transacao() as con:
        return con.execute(
            "SELECT * FROM itens_venda WHERE venda_id = ? ORDER BY id", (venda_id,)
        ).fetchall()


# --------------------------------------------------------------------------- #
# Agregações usadas no fechamento e na planilha
# --------------------------------------------------------------------------- #


def total_vendido(caixa_id: int) -> int:
    with transacao() as con:
        linha = con.execute(
            """
            SELECT COALESCE(SUM(total_centavos), 0) AS total
              FROM vendas WHERE caixa_id = ? AND cancelada = 0
            """,
            (caixa_id,),
        ).fetchone()
    return int(linha["total"])


def resumo_por_produto(caixa_id: int) -> list:
    with transacao() as con:
        return con.execute(
            """
            SELECT i.nome_produto,
                   i.categoria,
                   SUM(i.quantidade)          AS quantidade,
                   SUM(i.subtotal_centavos)   AS total_centavos
              FROM itens_venda i
              JOIN vendas v ON v.id = i.venda_id
             WHERE v.caixa_id = ? AND v.cancelada = 0
          GROUP BY i.nome_produto, i.categoria
          ORDER BY total_centavos DESC
            """,
            (caixa_id,),
        ).fetchall()


def resumo_por_funcionario(caixa_id: int) -> list:
    with transacao() as con:
        return con.execute(
            """
            SELECT f.nome                          AS vendedor,
                   COUNT(DISTINCT v.id)            AS qtd_vendas,
                   COALESCE(SUM(v.total_centavos), 0) AS total_centavos
              FROM vendas v
              JOIN funcionarios f ON f.id = v.funcionario_id
             WHERE v.caixa_id = ? AND v.cancelada = 0
          GROUP BY f.nome
          ORDER BY total_centavos DESC
            """,
            (caixa_id,),
        ).fetchall()


def resumo_por_pagamento(caixa_id: int) -> list:
    with transacao() as con:
        return con.execute(
            """
            SELECT forma_pagamento,
                   COUNT(*)                            AS qtd_vendas,
                   COALESCE(SUM(total_centavos), 0)    AS total_centavos
              FROM vendas
             WHERE caixa_id = ? AND cancelada = 0
          GROUP BY forma_pagamento
          ORDER BY total_centavos DESC
            """,
            (caixa_id,),
        ).fetchall()
