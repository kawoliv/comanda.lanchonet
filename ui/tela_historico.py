"""
Histórico: consulta dos caixas já fechados.

Responde às perguntas do dia a dia — "quanto vendemos terça?",
"quem estava no caixa?", "cadê a planilha daquele dia?".
"""

import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from core import planilha as gerador_planilha
from core import repositorio, servicos
from core.moeda import formatar
from ui.componentes import abrir_no_sistema, cartao_indicador, tabela
from ui.estilo import CORES


class TelaHistorico(ttk.Frame):
    def __init__(self, pai, app):
        super().__init__(pai, style="TFrame")
        self.app = app
        self.caixas = {}

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 12))
        ttk.Label(barra, text="Histórico de caixas", style="Titulo.TLabel").pack(side="left")

        self._montar_filtros()
        self._montar_indicadores()
        self._montar_listas()

    # ------------------------------------------------------------------ #

    def _montar_filtros(self):
        painel = tk.Frame(self, bg=CORES["painel"], highlightbackground=CORES["borda"],
                          highlightthickness=1)
        painel.pack(fill="x", pady=(0, 12))

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=(16, 12))
        interno.pack(fill="x")

        ttk.Label(interno, text="De", style="Painel.TLabel").pack(side="left", padx=(0, 6))
        self.campo_inicio = ttk.Entry(interno, width=12, font=("TkDefaultFont", 11),
                                      justify="center")
        self.campo_inicio.pack(side="left", ipady=3)

        ttk.Label(interno, text="até", style="Painel.TLabel").pack(side="left", padx=6)
        self.campo_fim = ttk.Entry(interno, width=12, font=("TkDefaultFont", 11),
                                   justify="center")
        self.campo_fim.pack(side="left", ipady=3)

        ttk.Label(interno, text="(dd/mm/aaaa)", style="Suave.TLabel").pack(side="left", padx=8)

        ttk.Button(interno, text="Filtrar", style="Primario.TButton",
                   command=self.carregar).pack(side="left", padx=(8, 0))

        for texto, dias in (("Últimos 7 dias", 7), ("Últimos 30 dias", 30), ("Tudo", None)):
            ttk.Button(interno, text=texto,
                       command=lambda d=dias: self._periodo_rapido(d)).pack(side="left", padx=(6, 0))

    def _montar_indicadores(self):
        self.indicadores = ttk.Frame(self)
        self.indicadores.pack(fill="x", pady=(0, 12))

        self.cartoes = {}
        for coluna, (chave, titulo) in enumerate([
            ("caixas", "Caixas no período"),
            ("vendas", "Vendas"),
            ("total", "Total faturado"),
            ("media", "Média por dia"),
        ]):
            cartao = cartao_indicador(self.indicadores, titulo, "—",
                                      CORES["sucesso"] if chave == "total" else None)
            cartao["quadro"].grid(row=0, column=coluna, sticky="ew", padx=(0, 10))
            self.indicadores.columnconfigure(coluna, weight=1)
            self.cartoes[chave] = cartao["valor"]

    def _montar_listas(self):
        corpo = ttk.Frame(self)
        corpo.pack(fill="both", expand=True)
        corpo.columnconfigure(0, weight=1, uniform="hist")
        corpo.columnconfigure(1, weight=1, uniform="hist")
        corpo.rowconfigure(0, weight=1)

        # Caixas -------------------------------------------------------- #
        esquerda = tk.Frame(corpo, bg=CORES["painel"], highlightbackground=CORES["borda"],
                            highlightthickness=1)
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        interno_esquerda = ttk.Frame(esquerda, style="Painel.TFrame", padding=16)
        interno_esquerda.pack(fill="both", expand=True)

        ttk.Label(interno_esquerda, text="Caixas fechados",
                  style="Subtitulo.TLabel").pack(anchor="w", pady=(0, 8))

        self.lista_caixas = tabela(interno_esquerda, [
            ("data", "Data", 88, "center"),
            ("caixa", "Nº", 38, "center"),
            ("operador", "Fechado por", 105, "w"),
            ("vendas", "Vendas", 68, "center"),
            ("total", "Total", 95, "e"),
            ("diferenca", "Dif.", 78, "e"),
        ], altura=7)
        self.lista_caixas.quadro.pack(fill="both", expand=True)
        self.lista_caixas.bind("<<TreeviewSelect>>", lambda _: self.mostrar_detalhe())

        acoes = ttk.Frame(interno_esquerda, style="Painel.TFrame")
        acoes.pack(fill="x", pady=(12, 0))
        ttk.Button(acoes, text="Abrir planilha", style="Primario.TButton",
                   command=self.abrir_planilha).pack(side="left", padx=(0, 8))
        ttk.Button(acoes, text="Gerar planilha novamente",
                   command=self.regerar_planilha).pack(side="left")

        # Detalhe ------------------------------------------------------- #
        direita = tk.Frame(corpo, bg=CORES["painel"], highlightbackground=CORES["borda"],
                           highlightthickness=1)
        direita.grid(row=0, column=1, sticky="nsew")
        interno_direita = ttk.Frame(direita, style="Painel.TFrame", padding=16)
        interno_direita.pack(fill="both", expand=True)

        self.rotulo_detalhe = ttk.Label(interno_direita, text="Selecione um caixa à esquerda",
                                        style="Subtitulo.TLabel")
        self.rotulo_detalhe.pack(anchor="w")
        self.rotulo_subdetalhe = ttk.Label(interno_direita, text="", style="Suave.TLabel")
        self.rotulo_subdetalhe.pack(anchor="w", pady=(2, 10))

        self.abas = ttk.Notebook(interno_direita)
        self.abas.pack(fill="both", expand=True)

        aba_produtos = ttk.Frame(self.abas, style="Painel.TFrame", padding=8)
        self.abas.add(aba_produtos, text="Produtos")
        self.lista_produtos = tabela(aba_produtos, [
            ("produto", "Produto", 200, "w"),
            ("qtd", "Qtd.", 60, "center"),
            ("total", "Total", 100, "e"),
        ], altura=7)
        self.lista_produtos.quadro.pack(fill="both", expand=True)

        aba_vendedores = ttk.Frame(self.abas, style="Painel.TFrame", padding=8)
        self.abas.add(aba_vendedores, text="Vendedores")
        self.lista_vendedores = tabela(aba_vendedores, [
            ("vendedor", "Vendedor", 180, "w"),
            ("qtd", "Vendas", 80, "center"),
            ("total", "Total", 100, "e"),
        ], altura=7)
        self.lista_vendedores.quadro.pack(fill="both", expand=True)

        aba_vendas = ttk.Frame(self.abas, style="Painel.TFrame", padding=8)
        self.abas.add(aba_vendas, text="Vendas")
        self.lista_vendas = tabela(aba_vendas, [
            ("id", "Nº", 50, "center"),
            ("hora", "Hora", 70, "center"),
            ("vendedor", "Vendedor", 130, "w"),
            ("pagamento", "Pagamento", 120, "w"),
            ("total", "Total", 92, "e"),
        ], altura=7)
        self.lista_vendas.quadro.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ #

    def ao_exibir(self):
        if not self.campo_inicio.get():
            self._periodo_rapido(30)
        else:
            self.carregar()

    def _periodo_rapido(self, dias):
        self.campo_inicio.delete(0, "end")
        self.campo_fim.delete(0, "end")
        if dias:
            hoje = date.today()
            self.campo_inicio.insert(0, (hoje - timedelta(days=dias)).strftime("%d/%m/%Y"))
            self.campo_fim.insert(0, hoje.strftime("%d/%m/%Y"))
        self.carregar()

    @staticmethod
    def _para_iso(texto: str) -> str:
        texto = texto.strip()
        if not texto:
            return ""
        for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                from datetime import datetime
                return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return ""

    def carregar(self):
        self.lista_caixas.delete(*self.lista_caixas.get_children())
        self.caixas.clear()

        registros = repositorio.listar_caixas(
            data_inicio=self._para_iso(self.campo_inicio.get()),
            data_fim=self._para_iso(self.campo_fim.get()),
        )

        total_geral = 0
        total_vendas = 0
        for caixa in registros:
            total_geral += int(caixa["total_centavos"])
            total_vendas += int(caixa["qtd_vendas"])
            diferenca = caixa["diferenca_centavos"]

            iid = self.lista_caixas.insert("", "end", values=(
                self._data_br(caixa["data_operacao"]),
                caixa["id"],
                caixa["operador_fechamento"] or "—",
                caixa["qtd_vendas"],
                formatar(caixa["total_centavos"]),
                formatar(diferenca) if diferenca is not None else "—",
            ))
            self.caixas[iid] = caixa

        self.cartoes["caixas"].configure(text=str(len(registros)))
        self.cartoes["vendas"].configure(text=str(total_vendas))
        self.cartoes["total"].configure(text=formatar(total_geral))
        self.cartoes["media"].configure(
            text=formatar(round(total_geral / len(registros)) if registros else 0)
        )

        self._limpar_detalhe()

    @staticmethod
    def _data_br(data_iso: str) -> str:
        partes = (data_iso or "").split("-")
        return f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else data_iso

    def _limpar_detalhe(self):
        self.rotulo_detalhe.configure(text="Selecione um caixa à esquerda")
        self.rotulo_subdetalhe.configure(text="")
        for lista in (self.lista_produtos, self.lista_vendedores, self.lista_vendas):
            lista.delete(*lista.get_children())

    def _caixa_selecionado(self):
        selecao = self.lista_caixas.selection()
        return self.caixas[selecao[0]] if selecao else None

    def mostrar_detalhe(self):
        caixa = self._caixa_selecionado()
        if caixa is None:
            return

        resumo = servicos.resumo_caixa(caixa["id"])

        self.rotulo_detalhe.configure(
            text=f"{self._data_br(caixa['data_operacao'])} — Caixa nº {caixa['id']}"
        )
        self.rotulo_subdetalhe.configure(
            text=f"Total {formatar(resumo['total_centavos'])}  ·  "
                 f"{resumo['qtd_vendas']} vendas  ·  {resumo['qtd_itens']} itens  ·  "
                 f"ticket médio {formatar(resumo['ticket_medio_centavos'])}"
        )

        self.lista_produtos.delete(*self.lista_produtos.get_children())
        for produto in resumo["por_produto"]:
            self.lista_produtos.insert("", "end", values=(
                produto["nome_produto"], produto["quantidade"],
                formatar(produto["total_centavos"]),
            ))

        self.lista_vendedores.delete(*self.lista_vendedores.get_children())
        for vendedor in resumo["por_funcionario"]:
            self.lista_vendedores.insert("", "end", values=(
                vendedor["vendedor"], vendedor["qtd_vendas"],
                formatar(vendedor["total_centavos"]),
            ))

        self.lista_vendas.delete(*self.lista_vendas.get_children())
        for venda in resumo["vendas"]:
            self.lista_vendas.insert("", "end", values=(
                venda["id"], venda["data_hora"][11:16], venda["vendedor"],
                venda["forma_pagamento"], formatar(venda["total_centavos"]),
            ))

    # ------------------------------------------------------------------ #

    def abrir_planilha(self):
        caixa = self._caixa_selecionado()
        if caixa is None:
            messagebox.showinfo("Selecione", "Escolha um caixa na lista.")
            return

        caminho = caixa["planilha"]
        if not caminho or not abrir_no_sistema(caminho):
            if messagebox.askyesno("Planilha não encontrada",
                                   "A planilha deste caixa não foi localizada.\n"
                                   "Deseja gerar novamente?"):
                self.regerar_planilha()

    def regerar_planilha(self):
        caixa = self._caixa_selecionado()
        if caixa is None:
            messagebox.showinfo("Selecione", "Escolha um caixa na lista.")
            return

        caminho = gerador_planilha.gerar(caixa["id"])
        repositorio.registrar_planilha(caixa["id"], caminho)
        self.carregar()

        if messagebox.askyesno("Planilha gerada", f"Arquivo salvo em:\n{caminho}\n\nAbrir agora?"):
            abrir_no_sistema(caminho)
