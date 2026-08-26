"""
Regras de negócio do caixa.

Toda regra ("não pode vender com caixa fechado", "só um caixa aberto por vez",
"quanto deveria ter na gaveta") vive aqui, e não dentro das telas. A interface
só chama estas funções e mostra o resultado.
"""

from datetime import datetime

from core import auth, repositorio
from core.moeda import formatar

FORMAS_PAGAMENTO = ["Dinheiro", "PIX", "Cartão de Débito", "Cartão de Crédito", "Vale-Refeição"]
CARGO_GERENTE = "Gerente"


class ErroDeNegocio(Exception):
    """Erro previsto, com mensagem pronta para mostrar ao funcionário."""


# --------------------------------------------------------------------------- #
# Funcionários e acesso administrativo
# --------------------------------------------------------------------------- #
#
# Só o cargo "Gerente" pode ter login/senha e, com isso, entrar no Modo
# Gerente (ver ui/janela.py). Guardamos essa regra aqui — e não na tela de
# Equipe — para que ela valha para qualquer chamador futuro.


def _eh_gerente(cargo: str) -> bool:
    return cargo.strip().lower() == CARGO_GERENTE.lower()


def criar_funcionario(nome: str, cargo: str = "Atendente",
                      login: str = "", senha: str = "") -> int:
    nome = nome.strip()
    cargo = cargo.strip() or "Atendente"
    if not nome:
        raise ErroDeNegocio("Informe o nome do funcionário.")

    login_salvo, hash_salvo = None, None
    if _eh_gerente(cargo):
        login = login.strip()
        if not login:
            raise ErroDeNegocio("Informe o login do Gerente.")
        if not senha:
            raise ErroDeNegocio("Informe a senha do Gerente.")
        login_salvo, hash_salvo = login, auth.gerar_hash_senha(senha)

    return repositorio.criar_funcionario(nome, cargo, login_salvo, hash_salvo)


def atualizar_funcionario(funcionario_id: int, nome: str, cargo: str,
                          login: str = "", senha: str = "") -> None:
    nome = nome.strip()
    cargo = cargo.strip() or "Atendente"
    if not nome:
        raise ErroDeNegocio("Informe o nome do funcionário.")

    login_salvo, hash_salvo = None, None
    if _eh_gerente(cargo):
        login = login.strip()
        if not login:
            raise ErroDeNegocio("Informe o login do Gerente.")
        if senha:
            hash_salvo = auth.gerar_hash_senha(senha)
        else:
            # Sem senha nova digitada: mantém o hash que já estava salvo.
            atual = repositorio.buscar_funcionario(funcionario_id)
            hash_salvo = atual["senha_hash"] if atual else None
            if not hash_salvo:
                raise ErroDeNegocio("Informe a senha do Gerente.")
        login_salvo = login

    repositorio.atualizar_funcionario(funcionario_id, nome, cargo, login_salvo, hash_salvo)


def autenticar_gerente(login: str, senha: str) -> dict:
    login = login.strip()
    funcionario = repositorio.buscar_funcionario_por_login(login) if login else None
    if (funcionario is None or not funcionario["ativo"]
            or not auth.verificar_senha(senha, funcionario["senha_hash"])):
        raise ErroDeNegocio("Login ou senha inválidos.")
    return funcionario


# --------------------------------------------------------------------------- #
# Abertura / fechamento
# --------------------------------------------------------------------------- #


def caixa_aberto():
    return repositorio.caixa_aberto()


def abrir_caixa(funcionario_id: int, valor_abertura_centavos: int = 0) -> int:
    if repositorio.caixa_aberto():
        raise ErroDeNegocio(
            "Já existe um caixa aberto. Feche o caixa atual antes de abrir outro."
        )
    if valor_abertura_centavos < 0:
        raise ErroDeNegocio("O valor de abertura não pode ser negativo.")

    agora = datetime.now()
    return repositorio.inserir_caixa(
        data_operacao=agora.strftime("%Y-%m-%d"),
        aberto_em=agora.strftime("%Y-%m-%d %H:%M:%S"),
        funcionario_id=funcionario_id,
        valor_abertura_centavos=valor_abertura_centavos,
    )


def fechar_caixa(
    caixa_id: int,
    funcionario_id: int,
    valor_contado_centavos: int,
    observacoes: str = "",
    gerar_planilha: bool = True,
):
    """
    Fecha o caixa, calcula a diferença de gaveta e gera a planilha do dia.

    Devolve (resumo, caminho_da_planilha).
    """
    from core import planilha  # import local evita dependência circular

    caixa = repositorio.buscar_caixa(caixa_id)
    if caixa is None:
        raise ErroDeNegocio("Caixa não encontrado.")
    if caixa["status"] == "FECHADO":
        raise ErroDeNegocio("Este caixa já foi fechado.")

    resumo = resumo_caixa(caixa_id)
    diferenca = valor_contado_centavos - resumo["esperado_gaveta_centavos"]
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    repositorio.marcar_caixa_fechado(
        caixa_id=caixa_id,
        fechado_em=agora,
        funcionario_id=funcionario_id,
        valor_contado_centavos=valor_contado_centavos,
        diferenca_centavos=diferenca,
        observacoes=observacoes.strip(),
    )

    caminho = None
    if gerar_planilha:
        caminho = planilha.gerar(caixa_id)
        repositorio.registrar_planilha(caixa_id, caminho)

    return resumo_caixa(caixa_id), caminho


# --------------------------------------------------------------------------- #
# Vendas
# --------------------------------------------------------------------------- #


def _normalizar_pagamentos(forma_pagamento: str, pagamentos: list, total_centavos: int) -> list:
    """Valida e devolve a composição canônica de pagamento de uma venda.

    Sem `pagamentos`, é uma venda de forma única (`forma_pagamento` cobre o
    total inteiro). Com `pagamentos`, o cliente dividiu entre duas formas
    diferentes — a soma tem que bater exatamente com o total da venda.
    """
    if not pagamentos:
        if forma_pagamento not in FORMAS_PAGAMENTO:
            raise ErroDeNegocio(f"Forma de pagamento inválida: {forma_pagamento}")
        return [{"forma_pagamento": forma_pagamento, "valor_centavos": total_centavos}]

    if len(pagamentos) != 2:
        raise ErroDeNegocio("A divisão de pagamento aceita exatamente duas formas.")

    formas = [pagamento["forma_pagamento"] for pagamento in pagamentos]
    if formas[0] == formas[1]:
        raise ErroDeNegocio("Escolha duas formas de pagamento diferentes.")
    for forma in formas:
        if forma not in FORMAS_PAGAMENTO:
            raise ErroDeNegocio(f"Forma de pagamento inválida: {forma}")

    valores = [int(pagamento["valor_centavos"]) for pagamento in pagamentos]
    if any(valor <= 0 for valor in valores):
        raise ErroDeNegocio("Os valores da divisão de pagamento devem ser maiores que zero.")
    if sum(valores) != total_centavos:
        raise ErroDeNegocio("A soma dos pagamentos não bate com o total da venda.")

    return [{"forma_pagamento": forma, "valor_centavos": valor}
            for forma, valor in zip(formas, valores)]


def registrar_venda(funcionario_id: int, itens: list, forma_pagamento: str = "Dinheiro",
                    pagamentos: list = None) -> dict:
    """
    Registra uma venda no caixa que estiver aberto.

    `itens` é uma lista de dicionários:
        {"produto_id": 1, "nome": "X-Burger", "categoria": "Lanches",
         "quantidade": 2, "preco_unit_centavos": 1800}

    Por padrão a venda é paga numa forma só (`forma_pagamento`). Para dividir
    entre duas formas diferentes, passe `pagamentos`:
        [{"forma_pagamento": "Dinheiro", "valor_centavos": 2000},
         {"forma_pagamento": "PIX", "valor_centavos": 1600}]
    Nesse caso `forma_pagamento` é ignorado — o texto salvo na venda vira as
    formas combinadas na ordem informada (ex.: "Dinheiro/PIX").
    """
    caixa = repositorio.caixa_aberto()
    if caixa is None:
        raise ErroDeNegocio("Nenhum caixa aberto. Abra o caixa para registrar vendas.")
    if not itens:
        raise ErroDeNegocio("Adicione pelo menos um produto antes de finalizar a venda.")

    for item in itens:
        if int(item["quantidade"]) <= 0:
            raise ErroDeNegocio(f'Quantidade inválida para "{item["nome"]}".')
        if int(item["preco_unit_centavos"]) < 0:
            raise ErroDeNegocio(f'Preço inválido para "{item["nome"]}".')

    total = sum(int(i["quantidade"]) * int(i["preco_unit_centavos"]) for i in itens)
    pagamentos_normalizados = _normalizar_pagamentos(forma_pagamento, pagamentos, total)
    forma_pagamento_exibicao = "/".join(p["forma_pagamento"] for p in pagamentos_normalizados)

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    venda_id = repositorio.inserir_venda(
        caixa_id=caixa["id"],
        funcionario_id=funcionario_id,
        data_hora=agora,
        forma_pagamento=forma_pagamento_exibicao,
        total_centavos=total,
        itens=itens,
        pagamentos=pagamentos_normalizados,
    )

    return {"venda_id": venda_id, "total_centavos": total, "data_hora": agora}


def cancelar_venda(venda_id: int, motivo: str = "") -> None:
    caixa = repositorio.caixa_aberto()
    if caixa is None:
        raise ErroDeNegocio("Só é possível cancelar vendas com o caixa aberto.")

    vendas = {v["id"] for v in repositorio.listar_vendas(caixa["id"])}
    if venda_id not in vendas:
        raise ErroDeNegocio("Esta venda não pertence ao caixa aberto e não pode ser cancelada.")

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repositorio.cancelar_venda(venda_id, agora, motivo.strip() or "Não informado")


# --------------------------------------------------------------------------- #
# Resumo
# --------------------------------------------------------------------------- #


def resumo_caixa(caixa_id: int) -> dict:
    """Junta tudo que o fechamento e a planilha precisam mostrar."""
    caixa = repositorio.buscar_caixa(caixa_id)
    if caixa is None:
        raise ErroDeNegocio("Caixa não encontrado.")

    vendas = repositorio.listar_vendas(caixa_id)
    validas = [v for v in vendas if not v["cancelada"]]
    canceladas = [v for v in vendas if v["cancelada"]]

    por_pagamento = repositorio.resumo_por_pagamento(caixa_id)
    total = sum(int(v["total_centavos"]) for v in validas)
    em_dinheiro = sum(
        int(p["total_centavos"]) for p in por_pagamento if p["forma_pagamento"] == "Dinheiro"
    )

    itens = repositorio.listar_itens_do_caixa(caixa_id)
    quantidade_itens = sum(int(i["quantidade"]) for i in itens)

    return {
        "caixa": caixa,
        "vendas": validas,
        "canceladas": canceladas,
        "itens": itens,
        "por_produto": repositorio.resumo_por_produto(caixa_id),
        "por_funcionario": repositorio.resumo_por_funcionario(caixa_id),
        "por_pagamento": por_pagamento,
        "qtd_vendas": len(validas),
        "qtd_canceladas": len(canceladas),
        "qtd_itens": quantidade_itens,
        "total_centavos": total,
        "total_cancelado_centavos": sum(int(v["total_centavos"]) for v in canceladas),
        "total_dinheiro_centavos": em_dinheiro,
        "ticket_medio_centavos": round(total / len(validas)) if validas else 0,
        # O que deveria estar na gaveta: troco inicial + o que entrou em dinheiro.
        # Cartão e PIX não passam pela gaveta.
        "esperado_gaveta_centavos": int(caixa["valor_abertura_centavos"]) + em_dinheiro,
    }


def texto_resumo(resumo: dict) -> str:
    """Versão em texto do resumo, usada na confirmação de fechamento."""
    return (
        f"Vendas registradas: {resumo['qtd_vendas']}\n"
        f"Itens vendidos: {resumo['qtd_itens']}\n"
        f"Total vendido: {formatar(resumo['total_centavos'])}\n"
        f"Ticket médio: {formatar(resumo['ticket_medio_centavos'])}\n"
        f"Esperado na gaveta: {formatar(resumo['esperado_gaveta_centavos'])}"
    )
