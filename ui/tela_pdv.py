"""
Tela de vendas (PDV) — é onde o atendente passa 99% do tempo.

Fluxo pensado para ser rápido no balcão:
    digita parte do nome -> Enter -> produto entra na comanda -> F2 finaliza.
Nada exige mouse.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from core import repositorio, servicos
from core.moeda import ValorInvalido, formatar, para_centavos
from ui.componentes import Dialogo, tabela
from ui.estilo import CORES


class TelaPDV(ttk.Frame):
    def __init__(self, pai, app):
        super().__init__(pai, style="TFrame")
        self.app = app
        self.comanda = []        # itens da venda em andamento
        self.produtos = {}       # iid da tabela -> linha do banco

        self._montar_cabecalho()
        self._montar_conteudo()
        self._montar_ultimas_vendas()

    # ------------------------------------------------------------------ #
    # Construção da tela
    # ------------------------------------------------------------------ #

    def _montar_cabecalho(self):
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 6))

        ttk.Label(barra, text="Frente de caixa", style="Titulo.TLabel").pack(side="left")

        self.rotulo_atalhos = ttk.Label(
            barra,
            text="Enter: adicionar   ·   Delete: remover item   ·   F2: finalizar venda",
            style="SuaveFundo.TLabel",
        )
        self.rotulo_atalhos.pack(side="right")

    def _montar_conteudo(self):
        conteudo = ttk.Frame(self)
        conteudo.pack(fill="both", expand=True)
        conteudo.columnconfigure(0, weight=3, uniform="pdv")
        conteudo.columnconfigure(1, weight=2, uniform="pdv")
        conteudo.rowconfigure(0, weight=1)

        self._painel_produtos(conteudo)
        self._painel_comanda(conteudo)

    def _painel_produtos(self, pai):
        painel = tk.Frame(pai, bg=CORES["painel"], highlightbackground=CORES["borda"],
                          highlightthickness=1)
        painel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=16)
        interno.pack(fill="both", expand=True)

        ttk.Label(interno, text="Produtos", style="Subtitulo.TLabel").pack(anchor="w")

        linha_busca = ttk.Frame(interno, style="Painel.TFrame")
        linha_busca.pack(fill="x", pady=(10, 12))

        self.campo_busca = ttk.Entry(linha_busca, style="Busca.TEntry",
                                     font=("TkDefaultFont", 13))
        self.campo_busca.pack(side="left", fill="x", expand=True, ipady=4)
        self.campo_busca.bind("<KeyRelease>", self._filtrar)
        self.campo_busca.bind("<Return>", lambda _: self.adicionar_a_comanda())
        self.campo_busca.bind("<Down>", self._focar_lista)

        ttk.Label(linha_busca, text="Qtd.", style="Painel.TLabel").pack(side="left", padx=(12, 6))
        self.quantidade = tk.StringVar(value="1")
        ttk.Spinbox(linha_busca, from_=1, to=99, width=4, textvariable=self.quantidade,
                    font=("TkDefaultFont", 13), justify="center").pack(side="left", ipady=4)

        ttk.Label(interno, text="Digite o nome do produto e pressione Enter",
                  style="Suave.TLabel").pack(anchor="w", pady=(0, 8))

        self.lista_produtos = tabela(interno, [
            ("nome", "Produto", 240, "w"),
            ("categoria", "Categoria", 120, "w"),
            ("preco", "Preço", 100, "e"),
        ], altura=9)
        self.lista_produtos.quadro.pack(fill="both", expand=True)
        self.lista_produtos.bind("<Double-1>", lambda _: self.adicionar_a_comanda())
        self.lista_produtos.bind("<Return>", lambda _: self.adicionar_a_comanda())

        ttk.Button(interno, text="Adicionar à comanda", style="Primario.TButton",
                   command=self.adicionar_a_comanda).pack(fill="x", pady=(12, 0))

    def _painel_comanda(self, pai):
        painel = tk.Frame(pai, bg=CORES["painel"], highlightbackground=CORES["borda"],
                          highlightthickness=1)
        painel.grid(row=0, column=1, sticky="nsew")

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=(16, 12))
        interno.pack(fill="both", expand=True)

        ttk.Label(interno, text="Comanda", style="Subtitulo.TLabel").pack(anchor="w")

        self.lista_comanda = tabela(interno, [
            ("produto", "Produto", 170, "w"),
            ("qtd", "Qtd.", 50, "center"),
            ("unit", "Unit.", 80, "e"),
            ("subtotal", "Subtotal", 90, "e"),
        ], altura=3)
        self.lista_comanda.quadro.pack(fill="both", expand=True, pady=(6, 4))
        self.lista_comanda.bind("<Delete>", lambda _: self.remover_item())

        acoes = ttk.Frame(interno, style="Painel.TFrame")
        acoes.pack(fill="x")
        for texto, comando in (("−", lambda: self._ajustar_quantidade(-1)),
                               ("+", lambda: self._ajustar_quantidade(1)),
                               ("Remover", self.remover_item),
                               ("Limpar", self.limpar_comanda)):
            ttk.Button(acoes, text=texto, command=comando).pack(side="left", padx=(0, 6))

        ttk.Separator(interno).pack(fill="x", pady=8)

        linha_total = ttk.Frame(interno, style="Painel.TFrame")
        linha_total.pack(fill="x")
        ttk.Label(linha_total, text="TOTAL", style="Painel.TLabel",
                  font=("TkDefaultFont", 11, "bold")).pack(side="left", pady=(4, 0))
        self.rotulo_total = ttk.Label(linha_total, text=formatar(0), style="Total.TLabel")
        self.rotulo_total.pack(side="right")

        formulario = ttk.Frame(interno, style="Painel.TFrame")
        formulario.pack(fill="x", pady=(8, 0))
        formulario.columnconfigure(1, weight=1)

        ttk.Label(formulario, text="Vendedor", style="Painel.TLabel").grid(
            row=0, column=0, sticky="w", pady=2, padx=(0, 10))
        self.combo_vendedor = ttk.Combobox(formulario, state="readonly",
                                           font=("TkDefaultFont", 11))
        self.combo_vendedor.grid(row=0, column=1, sticky="ew", pady=2, ipady=2)

        ttk.Label(formulario, text="Pagamento", style="Painel.TLabel").grid(
            row=1, column=0, sticky="w", pady=2, padx=(0, 10))
        self.combo_pagamento = ttk.Combobox(formulario, state="readonly",
                                            values=servicos.FORMAS_PAGAMENTO,
                                            font=("TkDefaultFont", 11))
        self.combo_pagamento.current(0)
        self.combo_pagamento.grid(row=1, column=1, sticky="ew", pady=2, ipady=2)
        self.combo_pagamento.bind("<<ComboboxSelected>>", lambda _: self._atualizar_troco())

        ttk.Label(formulario, text="Recebido", style="Painel.TLabel").grid(
            row=2, column=0, sticky="w", pady=2, padx=(0, 10))
        self.campo_recebido = ttk.Entry(formulario, font=("TkDefaultFont", 11))
        self.campo_recebido.grid(row=2, column=1, sticky="ew", pady=2, ipady=2)
        self.campo_recebido.bind("<KeyRelease>", lambda _: self._atualizar_troco())

        self.rotulo_troco = ttk.Label(interno, text="", style="Painel.TLabel",
                                      font=("TkDefaultFont", 12, "bold"),
                                      foreground=CORES["sucesso"])
        self.rotulo_troco.pack(anchor="e", pady=(2, 0))

        self.botao_finalizar = ttk.Button(interno, text="FINALIZAR VENDA   (F2)",
                                          style="Sucesso.TButton", command=self.finalizar_venda)
        self.botao_finalizar.pack(fill="x", pady=(8, 0))

    def _montar_ultimas_vendas(self):
        """
        Barra compacta com a última venda.

        A lista completa fica num diálogo à parte: o cancelamento é uma ação
        rara e sensível, não precisa ocupar espaço permanente na tela de venda.
        """
        painel = tk.Frame(self, bg=CORES["painel"], highlightbackground=CORES["borda"],
                          highlightthickness=1)
        painel.pack(fill="x", pady=(8, 0))

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=(16, 6))
        interno.pack(fill="x")

        self.rotulo_ultima = ttk.Label(interno, text="Nenhuma venda registrada ainda.",
                                       style="Painel.TLabel")
        self.rotulo_ultima.pack(side="left")

        ttk.Button(interno, text="Ver vendas do caixa",
                   command=self.abrir_vendas_do_caixa).pack(side="right")

    # ------------------------------------------------------------------ #
    # Carga de dados
    # ------------------------------------------------------------------ #

    def ao_exibir(self):
        self._carregar_produtos()
        self._carregar_vendedores()
        self._carregar_ultimas_vendas()
        self._atualizar_bloqueio()
        self.campo_busca.focus_set()

    def _carregar_produtos(self, termo: str = ""):
        self.lista_produtos.delete(*self.lista_produtos.get_children())
        self.produtos.clear()

        for produto in repositorio.listar_produtos(termo):
            iid = self.lista_produtos.insert("", "end", values=(
                produto["nome"], produto["categoria"], formatar(produto["preco_centavos"])
            ))
            self.produtos[iid] = produto

        primeiro = self.lista_produtos.get_children()
        if primeiro:
            self.lista_produtos.selection_set(primeiro[0])

    def _carregar_vendedores(self):
        funcionarios = repositorio.listar_funcionarios()
        self.vendedores = funcionarios
        self.combo_vendedor["values"] = [f["nome"] for f in funcionarios]

        if funcionarios:
            nomes = [f["nome"] for f in funcionarios]
            atual = self.app.operador["nome"] if self.app.operador else None
            self.combo_vendedor.current(nomes.index(atual) if atual in nomes else 0)

    def _carregar_ultimas_vendas(self):
        caixa = servicos.caixa_aberto()
        if caixa is None:
            self.rotulo_ultima.configure(text="Caixa fechado.")
            return

        vendas = [v for v in repositorio.listar_vendas(caixa["id"]) if not v["cancelada"]]
        if not vendas:
            self.rotulo_ultima.configure(text="Nenhuma venda registrada ainda.")
            return

        ultima = vendas[-1]
        self.rotulo_ultima.configure(
            text=f"Última venda:  nº {ultima['id']}  ·  {ultima['data_hora'][11:16]}  ·  "
                 f"{ultima['vendedor']}  ·  {ultima['forma_pagamento']}  ·  "
                 f"{formatar(ultima['total_centavos'])}"
        )

    def abrir_vendas_do_caixa(self):
        caixa = servicos.caixa_aberto()
        if caixa is None:
            messagebox.showinfo("Vendas do caixa", "Nenhum caixa aberto no momento.")
            return

        DialogoVendasDoCaixa(self.app, caixa["id"]).aguardar()
        self._carregar_ultimas_vendas()
        self.app.atualizar_cabecalho()

    def _atualizar_bloqueio(self):
        """Com o caixa fechado, o botão de finalizar fica desabilitado."""
        aberto = servicos.caixa_aberto() is not None
        estado = "normal" if aberto else "disabled"
        self.botao_finalizar.configure(state=estado)
        self.rotulo_atalhos.configure(
            text="Enter: adicionar   ·   Delete: remover item   ·   F2: finalizar venda"
            if aberto else "⚠  Caixa fechado — abra o caixa para registrar vendas."
        )

    # ------------------------------------------------------------------ #
    # Comanda
    # ------------------------------------------------------------------ #

    def _filtrar(self, evento=None):
        if evento and evento.keysym in ("Return", "Down", "Up"):
            return
        self._carregar_produtos(self.campo_busca.get())

    def _focar_lista(self, _evento=None):
        filhos = self.lista_produtos.get_children()
        if filhos:
            self.lista_produtos.focus_set()
            self.lista_produtos.selection_set(filhos[0])
            self.lista_produtos.focus(filhos[0])

    def adicionar_a_comanda(self):
        selecao = self.lista_produtos.selection()
        if not selecao:
            filhos = self.lista_produtos.get_children()
            if not filhos:
                return
            selecao = (filhos[0],)

        produto = self.produtos[selecao[0]]

        try:
            quantidade = int(self.quantidade.get())
        except ValueError:
            quantidade = 1
        quantidade = max(1, quantidade)

        for item in self.comanda:
            if item["produto_id"] == produto["id"]:
                item["quantidade"] += quantidade
                break
        else:
            self.comanda.append({
                "produto_id": produto["id"],
                "nome": produto["nome"],
                "categoria": produto["categoria"],
                "quantidade": quantidade,
                "preco_unit_centavos": produto["preco_centavos"],
            })

        self.quantidade.set("1")
        self.campo_busca.delete(0, "end")
        self._carregar_produtos()
        self._atualizar_comanda()
        self.campo_busca.focus_set()

    def _item_selecionado(self):
        selecao = self.lista_comanda.selection()
        if not selecao:
            return None
        return self.comanda[self.lista_comanda.index(selecao[0])]

    def _ajustar_quantidade(self, delta: int):
        item = self._item_selecionado()
        if item is None:
            return
        item["quantidade"] += delta
        if item["quantidade"] <= 0:
            self.comanda.remove(item)
        self._atualizar_comanda()

    def remover_item(self):
        item = self._item_selecionado()
        if item is not None:
            self.comanda.remove(item)
            self._atualizar_comanda()

    def limpar_comanda(self):
        if self.comanda and messagebox.askyesno("Limpar comanda",
                                                "Remover todos os itens da comanda?"):
            self.comanda.clear()
            self._atualizar_comanda()

    def _atualizar_comanda(self):
        self.lista_comanda.delete(*self.lista_comanda.get_children())
        for item in self.comanda:
            subtotal = item["quantidade"] * item["preco_unit_centavos"]
            self.lista_comanda.insert("", "end", values=(
                item["nome"], item["quantidade"],
                formatar(item["preco_unit_centavos"]), formatar(subtotal),
            ))
        self.rotulo_total.configure(text=formatar(self._total()))
        self._atualizar_troco()

    def _total(self) -> int:
        return sum(i["quantidade"] * i["preco_unit_centavos"] for i in self.comanda)

    def _atualizar_troco(self):
        if self.combo_pagamento.get() != "Dinheiro" or not self.campo_recebido.get().strip():
            self.rotulo_troco.configure(text="")
            return
        try:
            recebido = para_centavos(self.campo_recebido.get())
        except ValorInvalido:
            self.rotulo_troco.configure(text="Valor inválido", foreground=CORES["perigo"])
            return

        diferenca = recebido - self._total()
        if diferenca < 0:
            self.rotulo_troco.configure(text=f"Faltam {formatar(-diferenca)}",
                                        foreground=CORES["perigo"])
        else:
            self.rotulo_troco.configure(text=f"Troco: {formatar(diferenca)}",
                                        foreground=CORES["sucesso"])

    # ------------------------------------------------------------------ #
    # Venda
    # ------------------------------------------------------------------ #

    def finalizar_venda(self):
        if not self.comanda:
            messagebox.showinfo("Comanda vazia", "Adicione ao menos um produto.")
            return
        if not self.combo_vendedor.get():
            messagebox.showwarning("Vendedor", "Selecione quem está realizando a venda.")
            return

        vendedor = self.vendedores[self.combo_vendedor.current()]

        try:
            venda = servicos.registrar_venda(
                funcionario_id=vendedor["id"],
                itens=self.comanda,
                forma_pagamento=self.combo_pagamento.get(),
            )
        except servicos.ErroDeNegocio as erro:
            messagebox.showwarning("Não foi possível registrar", str(erro))
            return

        mensagem = (f"Venda nº {venda['venda_id']} registrada.\n"
                    f"Total: {formatar(venda['total_centavos'])}")
        if self.rotulo_troco.cget("text").startswith("Troco"):
            mensagem += f"\n{self.rotulo_troco.cget('text')}"

        self.comanda.clear()
        self.campo_recebido.delete(0, "end")
        self._atualizar_comanda()
        self._carregar_ultimas_vendas()
        self.app.atualizar_cabecalho()
        self.campo_busca.focus_set()

        messagebox.showinfo("Venda registrada", mensagem)

class DialogoVendasDoCaixa(Dialogo):
    """Lista as vendas do caixa aberto e permite cancelar uma delas."""

    def __init__(self, pai, caixa_id: int):
        super().__init__(pai, "Vendas do caixa", 900, 560)
        self.caixa_id = caixa_id

        ttk.Label(self.corpo,
                  text="Uma venda cancelada continua no histórico, mas sai do total do dia.",
                  style="Suave.TLabel").pack(anchor="w", pady=(0, 8))

        self.lista = tabela(self.corpo, [
            ("id", "Nº", 55, "center"),
            ("hora", "Hora", 70, "center"),
            ("vendedor", "Vendedor", 140, "w"),
            ("itens", "Itens", 250, "w"),
            ("pagamento", "Pagamento", 130, "w"),
            ("total", "Total", 100, "e"),
            ("situacao", "Situação", 95, "center"),
        ], altura=12)
        self.lista.quadro.pack(fill="both", expand=True)
        self.lista.tag_configure("cancelada", foreground="#B0B7BF")

        barra = ttk.Frame(self.corpo, style="Painel.TFrame")
        barra.pack(fill="x", pady=(12, 0))
        ttk.Button(barra, text="Fechar", command=self.destroy).pack(side="right")
        ttk.Button(barra, text="Cancelar venda selecionada", style="Perigo.TButton",
                   command=self.cancelar_venda).pack(side="right", padx=(0, 8))

        self.carregar()

    def carregar(self):
        self.lista.delete(*self.lista.get_children())

        for venda in reversed(repositorio.listar_vendas(self.caixa_id)):
            itens = repositorio.itens_da_venda(venda["id"])
            descricao = ", ".join(f"{i['quantidade']}x {i['nome_produto']}" for i in itens)
            if len(descricao) > 42:
                descricao = descricao[:39] + "..."

            self.lista.insert("", "end", iid=str(venda["id"]), values=(
                venda["id"],
                venda["data_hora"][11:16],
                venda["vendedor"],
                descricao,
                venda["forma_pagamento"],
                formatar(venda["total_centavos"]),
                "CANCELADA" if venda["cancelada"] else "OK",
            ), tags=("cancelada",) if venda["cancelada"] else ())

    def cancelar_venda(self):
        selecao = self.lista.selection()
        if not selecao:
            messagebox.showinfo("Cancelar venda", "Selecione a venda na lista.", parent=self)
            return

        venda_id = int(selecao[0])
        valores = self.lista.item(selecao[0], "values")
        if valores[6] == "CANCELADA":
            messagebox.showinfo("Cancelar venda", "Esta venda já está cancelada.", parent=self)
            return

        confirmado = messagebox.askyesno(
            "Cancelar venda",
            f"Cancelar a venda nº {venda_id} no valor de {valores[5]}?",
            parent=self,
        )
        if not confirmado:
            return

        try:
            servicos.cancelar_venda(venda_id, motivo="Cancelada no PDV")
        except servicos.ErroDeNegocio as erro:
            messagebox.showwarning("Não foi possível cancelar", str(erro), parent=self)
            return

        self.carregar()
