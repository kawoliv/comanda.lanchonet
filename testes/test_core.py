"""
Testes das regras de negócio (sem abrir a interface).

Rodar:
    python -m unittest discover testes
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


class TesteBase(unittest.TestCase):
    """Cada teste roda em um banco novo e temporário."""

    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        os.environ["CAIXA_DB"] = str(Path(self.temporario.name) / "teste.db")

        from core import db, repositorio
        db.inicializar()

        self.db = db
        self.repositorio = repositorio
        self.funcionario_id = repositorio.criar_funcionario("Ana", "Atendente")
        self.produto = repositorio.buscar_produto(
            repositorio.criar_produto("X-Burger Teste", "Lanches", 1800)
        )

    def tearDown(self):
        os.environ.pop("CAIXA_DB", None)
        self.temporario.cleanup()

    def item(self, quantidade=1, preco=None):
        return {
            "produto_id": self.produto["id"],
            "nome": self.produto["nome"],
            "categoria": self.produto["categoria"],
            "quantidade": quantidade,
            "preco_unit_centavos": preco if preco is not None else self.produto["preco_centavos"],
        }


class TesteMoeda(unittest.TestCase):
    def test_converte_formatos_digitados_pelo_usuario(self):
        from core.moeda import para_centavos
        self.assertEqual(para_centavos("12,50"), 1250)
        self.assertEqual(para_centavos("12.50"), 1250)
        self.assertEqual(para_centavos("R$ 1.234,56"), 123456)
        self.assertEqual(para_centavos(7), 700)
        self.assertEqual(para_centavos(0), 0)

    def test_recusa_texto_invalido(self):
        from core.moeda import ValorInvalido, para_centavos
        for entrada in ("abc", "", "12,,5"):
            with self.assertRaises(ValorInvalido):
                para_centavos(entrada)

    def test_formata_em_padrao_brasileiro(self):
        from core.moeda import formatar
        self.assertEqual(formatar(1250), "R$ 12,50")
        self.assertEqual(formatar(123456), "R$ 1.234,56")
        self.assertEqual(formatar(0), "R$ 0,00")

    def test_soma_em_centavos_nao_perde_precisao(self):
        """O clássico 0.1 + 0.2 != 0.3 que quebra fechamento de caixa."""
        from core.moeda import para_centavos
        total = sum(para_centavos("0,10") for _ in range(10))
        self.assertEqual(total, para_centavos("1,00"))


class TesteAberturaFechamento(TesteBase):
    def test_nao_permite_dois_caixas_abertos(self):
        from core.servicos import ErroDeNegocio, abrir_caixa
        abrir_caixa(self.funcionario_id, 10000)
        with self.assertRaises(ErroDeNegocio):
            abrir_caixa(self.funcionario_id, 5000)

    def test_venda_sem_caixa_aberto_e_recusada(self):
        from core.servicos import ErroDeNegocio, registrar_venda
        with self.assertRaises(ErroDeNegocio):
            registrar_venda(self.funcionario_id, [self.item()])

    def test_fechamento_calcula_diferenca_da_gaveta(self):
        from core.servicos import abrir_caixa, fechar_caixa, registrar_venda

        caixa_id = abrir_caixa(self.funcionario_id, 10000)          # R$ 100,00 de troco
        registrar_venda(self.funcionario_id, [self.item(2)], "Dinheiro")   # R$ 36,00
        registrar_venda(self.funcionario_id, [self.item(1)], "PIX")        # R$ 18,00

        resumo, _ = fechar_caixa(caixa_id, self.funcionario_id,
                                 valor_contado_centavos=13600, gerar_planilha=False)

        self.assertEqual(resumo["total_centavos"], 5400)             # 36 + 18
        self.assertEqual(resumo["total_dinheiro_centavos"], 3600)    # só o dinheiro
        self.assertEqual(resumo["esperado_gaveta_centavos"], 13600)  # 100 + 36
        self.assertEqual(resumo["caixa"]["diferenca_centavos"], 0)
        self.assertEqual(resumo["caixa"]["status"], "FECHADO")

    def test_fechamento_registra_quebra_de_caixa(self):
        from core.servicos import abrir_caixa, fechar_caixa, registrar_venda

        caixa_id = abrir_caixa(self.funcionario_id, 0)
        registrar_venda(self.funcionario_id, [self.item(1)], "Dinheiro")  # R$ 18,00
        resumo, _ = fechar_caixa(caixa_id, self.funcionario_id,
                                 valor_contado_centavos=1700, gerar_planilha=False)

        self.assertEqual(resumo["caixa"]["diferenca_centavos"], -100)  # faltou R$ 1,00

    def test_nao_fecha_duas_vezes(self):
        from core.servicos import ErroDeNegocio, abrir_caixa, fechar_caixa
        caixa_id = abrir_caixa(self.funcionario_id, 0)
        fechar_caixa(caixa_id, self.funcionario_id, 0, gerar_planilha=False)
        with self.assertRaises(ErroDeNegocio):
            fechar_caixa(caixa_id, self.funcionario_id, 0, gerar_planilha=False)


class TesteVendas(TesteBase):
    def test_registra_venda_com_itens_e_horario(self):
        from core.servicos import abrir_caixa, registrar_venda

        caixa_id = abrir_caixa(self.funcionario_id, 0)
        venda = registrar_venda(self.funcionario_id, [self.item(3)], "Cartão de Débito")

        self.assertEqual(venda["total_centavos"], 5400)
        itens = self.repositorio.itens_da_venda(venda["venda_id"])
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["quantidade"], 3)
        self.assertEqual(itens[0]["nome_produto"], "X-Burger Teste")
        self.assertRegex(venda["data_hora"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_venda_vazia_e_recusada(self):
        from core.servicos import ErroDeNegocio, abrir_caixa, registrar_venda
        abrir_caixa(self.funcionario_id, 0)
        with self.assertRaises(ErroDeNegocio):
            registrar_venda(self.funcionario_id, [])

    def test_venda_cancelada_sai_do_total(self):
        from core.servicos import (abrir_caixa, cancelar_venda, registrar_venda,
                                   resumo_caixa)

        caixa_id = abrir_caixa(self.funcionario_id, 0)
        registrar_venda(self.funcionario_id, [self.item(1)])
        venda = registrar_venda(self.funcionario_id, [self.item(1)])
        cancelar_venda(venda["venda_id"], "Cliente desistiu")

        resumo = resumo_caixa(caixa_id)
        self.assertEqual(resumo["qtd_vendas"], 1)
        self.assertEqual(resumo["total_centavos"], 1800)
        self.assertEqual(resumo["total_cancelado_centavos"], 1800)

    def test_preco_do_item_e_congelado_na_venda(self):
        """Mudar o preço no cardápio não pode alterar o histórico."""
        from core.servicos import abrir_caixa, registrar_venda, resumo_caixa

        caixa_id = abrir_caixa(self.funcionario_id, 0)
        registrar_venda(self.funcionario_id, [self.item(1)])
        self.repositorio.atualizar_produto(self.produto["id"], "X-Burger Teste", "Lanches", 9900)

        self.assertEqual(resumo_caixa(caixa_id)["total_centavos"], 1800)


class TestePlanilha(TesteBase):
    def test_gera_arquivo_com_as_quatro_abas(self):
        from openpyxl import load_workbook

        from core.servicos import abrir_caixa, fechar_caixa, registrar_venda

        caixa_id = abrir_caixa(self.funcionario_id, 5000)
        registrar_venda(self.funcionario_id, [self.item(2)], "Dinheiro")

        destino = Path(self.temporario.name)
        from core import planilha
        _, caminho = fechar_caixa(caixa_id, self.funcionario_id, 8600, gerar_planilha=False)
        caminho = planilha.gerar(caixa_id, pasta_destino=destino)

        self.assertTrue(caminho.exists())
        livro = load_workbook(caminho)
        self.assertEqual(livro.sheetnames,
                         ["Resumo", "Vendas do Dia", "Por Produto", "Por Funcionário"])
        self.assertEqual(livro["Vendas do Dia"]["D4"].value, "X-Burger Teste")
        self.assertEqual(livro["Vendas do Dia"]["F4"].value, 2)


class TesteHistorico(TesteBase):
    def test_caixa_fechado_aparece_na_consulta(self):
        from core.servicos import abrir_caixa, fechar_caixa, registrar_venda

        caixa_id = abrir_caixa(self.funcionario_id, 0)
        registrar_venda(self.funcionario_id, [self.item(2)])
        fechar_caixa(caixa_id, self.funcionario_id, 3600, gerar_planilha=False)

        historico = self.repositorio.listar_caixas()
        self.assertEqual(len(historico), 1)
        self.assertEqual(historico[0]["total_centavos"], 3600)
        self.assertEqual(historico[0]["qtd_vendas"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
