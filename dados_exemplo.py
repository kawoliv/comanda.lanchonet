"""
Gera dados de demonstração: alguns dias de caixa já fechados + um caixa aberto.

Serve para testar o sistema sem precisar digitar vendas na mão.

Uso:
    python dados_exemplo.py
"""

import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import db, planilha, repositorio  # noqa: E402
from core.moeda import formatar  # noqa: E402

EQUIPE = [("Ana Souza", "Atendente"), ("Bruno Lima", "Atendente"), ("Carla Dias", "Caixa")]
PAGAMENTOS = ["Dinheiro", "Dinheiro", "PIX", "PIX", "Cartão de Débito", "Cartão de Crédito"]

DIAS_ANTERIORES = 6
VENDAS_POR_DIA = (18, 34)
ITENS_POR_VENDA = (1, 4)


def _criar_equipe() -> list:
    ids = []
    for nome, cargo in EQUIPE:
        try:
            ids.append(repositorio.criar_funcionario(nome, cargo))
        except sqlite3.IntegrityError:
            existente = [f for f in repositorio.listar_funcionarios() if f["nome"] == nome]
            ids.append(existente[0]["id"])
    return ids


def _simular_dia(data: datetime, funcionarios: list, produtos: list, fechar: bool) -> int:
    caixa_id = repositorio.inserir_caixa(
        data_operacao=data.strftime("%Y-%m-%d"),
        aberto_em=data.replace(hour=8, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
        funcionario_id=funcionarios[0],
        valor_abertura_centavos=10000,
    )

    total_dinheiro = 0
    for _ in range(random.randint(*VENDAS_POR_DIA)):
        hora = data.replace(
            hour=random.randint(9, 21), minute=random.randint(0, 59), second=random.randint(0, 59)
        )
        pagamento = random.choice(PAGAMENTOS)

        itens = []
        for produto in random.sample(produtos, random.randint(*ITENS_POR_VENDA)):
            itens.append({
                "produto_id": produto["id"],
                "nome": produto["nome"],
                "categoria": produto["categoria"],
                "quantidade": random.randint(1, 3),
                "preco_unit_centavos": produto["preco_centavos"],
            })

        total = sum(i["quantidade"] * i["preco_unit_centavos"] for i in itens)
        if pagamento == "Dinheiro":
            total_dinheiro += total

        repositorio.inserir_venda(
            caixa_id=caixa_id,
            funcionario_id=random.choice(funcionarios),
            data_hora=hora.strftime("%Y-%m-%d %H:%M:%S"),
            forma_pagamento=pagamento,
            total_centavos=total,
            itens=itens,
        )

    if fechar:
        esperado = 10000 + total_dinheiro
        contado = esperado + random.choice([0, 0, 0, -200, 150])  # pequenas quebras de caixa
        repositorio.marcar_caixa_fechado(
            caixa_id=caixa_id,
            fechado_em=data.replace(hour=22, minute=15).strftime("%Y-%m-%d %H:%M:%S"),
            funcionario_id=funcionarios[-1],
            valor_contado_centavos=contado,
            diferenca_centavos=contado - esperado,
            observacoes="",
        )
        repositorio.registrar_planilha(caixa_id, planilha.gerar(caixa_id))

    return caixa_id


def main() -> None:
    random.seed(7)
    db.inicializar()

    funcionarios = _criar_equipe()
    produtos = list(repositorio.listar_produtos())
    hoje = datetime.now()

    for dias_atras in range(DIAS_ANTERIORES, 0, -1):
        caixa_id = _simular_dia(hoje - timedelta(days=dias_atras), funcionarios, produtos, True)
        total = repositorio.total_vendido(caixa_id)
        print(f"Caixa {caixa_id:>2} — {(hoje - timedelta(days=dias_atras)):%d/%m/%Y} "
              f"fechado com {formatar(total)}")

    if repositorio.caixa_aberto() is None:
        caixa_id = _simular_dia(hoje, funcionarios, produtos, False)
        print(f"Caixa {caixa_id:>2} — {hoje:%d/%m/%Y} EM ABERTO "
              f"com {formatar(repositorio.total_vendido(caixa_id))}")

    print("\nDados de exemplo criados. Rode 'python app.py' para abrir o sistema.")


if __name__ == "__main__":
    main()
