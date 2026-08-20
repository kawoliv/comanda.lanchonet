"""
Abertura e fechamento do caixa.

O fechamento é o momento crítico do dia: confere a gaveta, trava as vendas
daquele turno e gera a planilha que o dono vai olhar depois.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from core import servicos
from core.moeda import ValorInvalido, formatar, para_centavos
from ui.componentes import abrir_no_sistema, cartao_indicador, tabela
from ui.estilo import CORES


class TelaFechamento(ttk.Frame):
    def __init__(self, pai, app):
        super().__init__(pai, style="TFrame")
        self.app = app
        self.caixa_id = None
        # Conferência de gaveta persiste enquanto o mesmo caixa segue aberto,
        # mesmo que a tela seja reconstruída (navegar de aba ou "Atualizar").
        # Isso impede reabrir a contagem às cegas só recarregando a tela.
        self.conferido = False
        self.valor_contado_centavos = None

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 12))
        ttk.Label(barra, text="Caixa do dia", style="Titulo.TLabel").pack(side="left")
        ttk.Button(barra, text="Atualizar", command=self.ao_exibir).pack(side="right")

        self.area = ttk.Frame(self)
        self.area.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ #

    def ao_exibir(self):
        for widget in self.area.winfo_children():
            widget.destroy()

        caixa = servicos.caixa_aberto()
        if caixa is None:
            self.caixa_id = None
            self.conferido = False
            self.valor_contado_centavos = None
            self._montar_caixa_fechado()
        else:
            if self.caixa_id != caixa["id"]:
                # Caixa diferente do que estava sendo conferido (ex.: reabriu
                # depois de fechar) — a contagem anterior não vale mais aqui.
                self.conferido = False
                self.valor_contado_centavos = None
            self.caixa_id = caixa["id"]
            self._montar_caixa_aberto(servicos.resumo_caixa(caixa["id"]))

    # ------------------------------------------------------------------ #
    # Estado: sem caixa aberto
    # ------------------------------------------------------------------ #

    def _montar_caixa_fechado(self):
        painel = tk.Frame(self.area, bg=CORES["painel"],
                          highlightbackground=CORES["borda"], highlightthickness=1)
        painel.pack(fill="both", expand=True)

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=40)
        interno.place(relx=0.5, rely=0.4, anchor="center")

        ttk.Label(interno, text="Nenhum caixa aberto", style="Subtitulo.TLabel").pack()
        ttk.Label(interno, text="Abra o caixa informando o troco inicial para começar a vender.",
                  style="Suave.TLabel").pack(pady=(6, 20))
        ttk.Button(interno, text="Abrir caixa", style="Sucesso.TButton",
                   command=self.app.abrir_caixa).pack(ipadx=20)

    # ------------------------------------------------------------------ #
    # Estado: caixa aberto
    # ------------------------------------------------------------------ #

    def _montar_caixa_aberto(self, resumo):
        caixa = resumo["caixa"]

        indicadores = ttk.Frame(self.area)
        indicadores.pack(fill="x", pady=(0, 12))
        dados = [
            ("Total vendido", formatar(resumo["total_centavos"]), CORES["sucesso"]),
            ("Vendas", str(resumo["qtd_vendas"]), None),
            ("Itens vendidos", str(resumo["qtd_itens"]), None),
            ("Ticket médio", formatar(resumo["ticket_medio_centavos"]), None),
        ]
        for coluna, (titulo, valor, cor) in enumerate(dados):
            cartao = cartao_indicador(indicadores, titulo, valor, cor)
            cartao["quadro"].grid(row=0, column=coluna, sticky="ew", padx=(0, 10))
            indicadores.columnconfigure(coluna, weight=1)

        corpo = ttk.Frame(self.area)
        corpo.pack(fill="both", expand=True)
        corpo.columnconfigure(0, weight=3, uniform="fech")
        corpo.columnconfigure(1, weight=2, uniform="fech")
        corpo.rowconfigure(0, weight=1)

        self._painel_movimento(corpo, resumo)
        self._painel_conferencia(corpo, caixa, resumo)

    def _painel_movimento(self, pai, resumo):
        painel = tk.Frame(pai, bg=CORES["painel"], highlightbackground=CORES["borda"],
                          highlightthickness=1)
        painel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=16)
        interno.pack(fill="both", expand=True)

        caixa = resumo["caixa"]
        ttk.Label(interno, text=f"Caixa nº {caixa['id']} — aberto por {caixa['operador_abertura']}",
                  style="Subtitulo.TLabel").pack(anchor="w")
        ttk.Label(interno,
                  text=f"Aberto em {caixa['aberto_em']}   ·   "
                       f"Troco inicial {formatar(caixa['valor_abertura_centavos'])}",
                  style="Suave.TLabel").pack(anchor="w", pady=(2, 14))

        ttk.Label(interno, text="Por forma de pagamento", style="Painel.TLabel",
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        lista_pagamento = tabela(interno, [
            ("forma", "Forma", 220, "w"),
            ("qtd", "Vendas", 90, "center"),
            ("total", "Total", 130, "e"),
        ], altura=4)
        lista_pagamento.quadro.pack(fill="x", pady=(6, 12))
        for pagamento in resumo["por_pagamento"]:
            lista_pagamento.insert("", "end", values=(
                pagamento["forma_pagamento"], pagamento["qtd_vendas"],
                formatar(pagamento["total_centavos"]),
            ))

        ttk.Label(interno, text="Produtos vendidos hoje", style="Painel.TLabel",
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        lista_produtos = tabela(interno, [
            ("produto", "Produto", 230, "w"),
            ("categoria", "Categoria", 130, "w"),
            ("qtd", "Qtd.", 70, "center"),
            ("total", "Total", 120, "e"),
        ], altura=6)
        lista_produtos.quadro.pack(fill="both", expand=True, pady=(6, 0))
        for produto in resumo["por_produto"]:
            lista_produtos.insert("", "end", values=(
                produto["nome_produto"], produto["categoria"],
                produto["quantidade"], formatar(produto["total_centavos"]),
            ))

    def _painel_conferencia(self, pai, caixa, resumo):
        painel = tk.Frame(pai, bg=CORES["painel"], highlightbackground=CORES["borda"],
                          highlightthickness=1)
        painel.grid(row=0, column=1, sticky="nsew")

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=16)
        interno.pack(fill="both", expand=True)

        ttk.Label(interno, text="Conferência da gaveta", style="Subtitulo.TLabel").pack(anchor="w")

        ttk.Label(interno,
                  text="Conte o dinheiro físico da gaveta antes de olhar qualquer total do "
                       "sistema. O valor esperado só aparece depois de você confirmar a "
                       "contagem — assim a conferência é confiável.",
                  style="Suave.TLabel", wraplength=320).pack(anchor="w", pady=(10, 14))

        ttk.Label(interno, text="Dinheiro contado na gaveta (R$)",
                  style="Painel.TLabel").pack(anchor="w")
        self.campo_contado = ttk.Entry(interno, font=("TkDefaultFont", 16))
        self.campo_contado.pack(fill="x", pady=(4, 4), ipady=6)
        self.campo_contado.bind("<Return>", lambda _: self._conferir_contagem(resumo))

        self.rotulo_erro_contagem = ttk.Label(interno, text="", style="Painel.TLabel",
                                              foreground=CORES["perigo"])
        self.rotulo_erro_contagem.pack(anchor="w", pady=(0, 8))

        self.botao_conferir = ttk.Button(interno, text="Conferir contagem",
                                         style="Primario.TButton",
                                         command=lambda: self._conferir_contagem(resumo))
        self.botao_conferir.pack(fill="x")

        # Revelado só depois da contagem confirmada — ver _conferir_contagem.
        self.frame_revelado = ttk.Frame(interno, style="Painel.TFrame")

        detalhes = ttk.Frame(self.frame_revelado, style="Painel.TFrame")
        detalhes.pack(fill="x", pady=(14, 4))
        detalhes.columnconfigure(1, weight=1)

        linhas = [
            ("(+) Troco inicial", formatar(caixa["valor_abertura_centavos"])),
            ("(+) Recebido em dinheiro", formatar(resumo["total_dinheiro_centavos"])),
            ("(=) Esperado na gaveta", formatar(resumo["esperado_gaveta_centavos"])),
        ]
        for indice, (rotulo, valor) in enumerate(linhas):
            negrito = indice == len(linhas) - 1
            ttk.Label(detalhes, text=rotulo, style="Painel.TLabel",
                      font=("TkDefaultFont", 11, "bold" if negrito else "normal")).grid(
                row=indice, column=0, sticky="w", pady=3)
            ttk.Label(detalhes, text=valor, style="Painel.TLabel",
                      font=("TkDefaultFont", 11, "bold" if negrito else "normal")).grid(
                row=indice, column=1, sticky="e", pady=3)

        ttk.Label(self.frame_revelado, text="Cartão, PIX e vale não passam pela gaveta.",
                  style="Suave.TLabel").pack(anchor="w", pady=(2, 10))

        self.rotulo_diferenca = ttk.Label(self.frame_revelado, text="", style="Painel.TLabel",
                                          font=("TkDefaultFont", 12, "bold"))
        self.rotulo_diferenca.pack(anchor="w")

        ttk.Separator(interno).pack(fill="x", pady=14)

        ttk.Label(interno, text="Observações (opcional)", style="Painel.TLabel").pack(anchor="w")
        self.campo_observacoes = tk.Text(interno, height=3, font=("TkDefaultFont", 10),
                                         relief="solid", borderwidth=1,
                                         highlightthickness=0, wrap="word")
        self.campo_observacoes.pack(fill="x", pady=(4, 12))

        self.botao_fechar = ttk.Button(interno, text="FECHAR CAIXA E GERAR PLANILHA",
                                       style="Sucesso.TButton", state="disabled",
                                       command=self.fechar_caixa)
        self.botao_fechar.pack(fill="x")
        ttk.Label(interno, text="Depois de fechado, o caixa não aceita mais vendas "
                                "e passa a ficar disponível no Histórico.",
                  style="Suave.TLabel", wraplength=320).pack(anchor="w", pady=(8, 0))

        if self.conferido:
            # Tela reconstruída (Atualizar / troca de aba) com este mesmo
            # caixa já conferido — reabre já travado, sem voltar à contagem cega.
            self.campo_contado.insert(0, formatar(self.valor_contado_centavos).replace("R$ ", ""))
            self._revelar(resumo, self.valor_contado_centavos)
        else:
            self.campo_contado.focus_set()

    def _conferir_contagem(self, resumo):
        try:
            contado = para_centavos(self.campo_contado.get())
        except ValorInvalido as erro:
            self.rotulo_erro_contagem.configure(text=str(erro))
            return

        self.rotulo_erro_contagem.configure(text="")
        self._revelar(resumo, contado)

    def _revelar(self, resumo, contado):
        self.conferido = True
        self.valor_contado_centavos = contado

        diferenca = contado - resumo["esperado_gaveta_centavos"]
        if diferenca == 0:
            self.rotulo_diferenca.configure(text="Gaveta conferida — sem diferença",
                                            foreground=CORES["sucesso"])
        elif diferenca > 0:
            self.rotulo_diferenca.configure(text=f"Sobra de {formatar(diferenca)}",
                                            foreground=CORES["aviso"])
        else:
            self.rotulo_diferenca.configure(text=f"Falta {formatar(-diferenca)}",
                                            foreground=CORES["perigo"])

        # Trava o valor contado: depois de revelado o esperado, não dá mais
        # para "ajustar" a contagem digitada às cegas.
        self.campo_contado.configure(state="readonly")
        self.botao_conferir.pack_forget()
        self.frame_revelado.pack(fill="x")
        self.botao_fechar.configure(state="normal")

    # ------------------------------------------------------------------ #

    def fechar_caixa(self):
        if not self.conferido or self.valor_contado_centavos is None:
            messagebox.showwarning("Conferência pendente",
                                    "Confirme a contagem da gaveta antes de fechar o caixa.")
            return
        contado = self.valor_contado_centavos

        resumo = servicos.resumo_caixa(self.caixa_id)
        diferenca = contado - resumo["esperado_gaveta_centavos"]

        mensagem = (
            f"{servicos.texto_resumo(resumo)}\n"
            f"Contado na gaveta: {formatar(contado)}\n"
            f"Diferença: {formatar(diferenca)}\n\n"
            "Confirma o fechamento? Esta ação não pode ser desfeita."
        )
        if not messagebox.askyesno("Fechar caixa", mensagem):
            return

        try:
            _, planilha = servicos.fechar_caixa(
                caixa_id=self.caixa_id,
                funcionario_id=self.app.operador["id"],
                valor_contado_centavos=contado,
                observacoes=self.campo_observacoes.get("1.0", "end").strip(),
            )
        except servicos.ErroDeNegocio as erro:
            messagebox.showwarning("Não foi possível fechar", str(erro))
            return

        self.app.atualizar_cabecalho()
        self.ao_exibir()

        abrir = messagebox.askyesno(
            "Caixa fechado",
            f"Caixa fechado com sucesso.\n\nPlanilha gerada em:\n{planilha}\n\n"
            "Deseja abrir a planilha agora?",
        )
        if abrir and not abrir_no_sistema(planilha):
            messagebox.showinfo("Planilha", f"Arquivo salvo em:\n{planilha}")
