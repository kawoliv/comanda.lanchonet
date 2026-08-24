"""Cadastro de produtos: incluir, editar preço e desativar itens do cardápio."""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from core import repositorio
from core.moeda import formatar
from ui.componentes import DialogoProduto, tabela
from ui.estilo import CORES


class TelaProdutos(ttk.Frame):
    def __init__(self, pai, app):
        super().__init__(pai, style="TFrame")
        self.app = app
        self.produtos = {}

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 12))
        ttk.Label(barra, text="Cardápio", style="Titulo.TLabel").pack(side="left")
        self.botao_novo = ttk.Button(barra, text="+  Novo produto", style="Primario.TButton",
                                     command=self.novo)
        self.botao_novo.pack(side="right")

        self.rotulo_bloqueio = ttk.Label(
            barra, text="🔒 Somente leitura — entre no Modo Gerente para editar o cardápio.",
            style="SuaveFundo.TLabel", foreground=CORES["aviso"],
        )

        painel = tk.Frame(self, bg=CORES["painel"], highlightbackground=CORES["borda"],
                          highlightthickness=1)
        painel.pack(fill="both", expand=True)

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=16)
        interno.pack(fill="both", expand=True)

        linha_busca = ttk.Frame(interno, style="Painel.TFrame")
        linha_busca.pack(fill="x", pady=(0, 12))
        ttk.Label(linha_busca, text="Buscar", style="Painel.TLabel").pack(side="left", padx=(0, 8))
        self.campo_busca = ttk.Entry(linha_busca, font=("TkDefaultFont", 12))
        self.campo_busca.pack(side="left", fill="x", expand=True, ipady=3)
        self.campo_busca.bind("<KeyRelease>", lambda _: self.carregar())

        self.lista = tabela(interno, [
            ("nome", "Produto", 300, "w"),
            ("categoria", "Categoria", 160, "w"),
            ("preco", "Preço", 120, "e"),
        ], altura=15)
        self.lista.quadro.pack(fill="both", expand=True)
        self.lista.bind("<Double-1>", lambda _: self.editar())

        acoes = ttk.Frame(interno, style="Painel.TFrame")
        acoes.pack(fill="x", pady=(12, 0))
        self.botao_editar = ttk.Button(acoes, text="Editar", command=self.editar)
        self.botao_editar.pack(side="left", padx=(0, 8))
        self.botao_remover = ttk.Button(acoes, text="Remover do cardápio", style="Perigo.TButton",
                                        command=self.desativar)
        self.botao_remover.pack(side="left")
        ttk.Label(acoes, text="Produtos removidos somem do PDV, mas continuam no histórico.",
                  style="Suave.TLabel").pack(side="right")

    def ao_exibir(self):
        self.carregar()
        self._atualizar_bloqueio()

    def _atualizar_bloqueio(self):
        """Criar/editar/remover produto (o preço, principalmente) exige Modo
        Gerente — sem ele a tela fica só para consulta."""
        liberado = self.app.modo_gerente
        estado = "normal" if liberado else "disabled"
        self.botao_novo.configure(state=estado)
        self.botao_editar.configure(state=estado)
        self.botao_remover.configure(state=estado)
        if liberado:
            self.rotulo_bloqueio.pack_forget()
        else:
            self.rotulo_bloqueio.pack(side="right")

    def carregar(self):
        self.lista.delete(*self.lista.get_children())
        self.produtos.clear()

        for produto in repositorio.listar_produtos(self.campo_busca.get()):
            iid = self.lista.insert("", "end", values=(
                produto["nome"], produto["categoria"], formatar(produto["preco_centavos"])
            ))
            self.produtos[iid] = produto

    def _selecionado(self):
        selecao = self.lista.selection()
        if not selecao:
            messagebox.showinfo("Selecione", "Escolha um produto na lista.")
            return None
        return self.produtos[selecao[0]]

    def _exige_modo_gerente(self) -> bool:
        if self.app.modo_gerente:
            return True
        messagebox.showwarning(
            "Modo Gerente necessário",
            "Entre no Modo Gerente (cabeçalho) para alterar o cardápio.",
        )
        return False

    def novo(self):
        if not self._exige_modo_gerente():
            return
        dados = DialogoProduto(self.app, repositorio.categorias()).aguardar()
        if not dados:
            return
        try:
            repositorio.criar_produto(**dados)
        except sqlite3.IntegrityError:
            messagebox.showwarning("Produto repetido",
                                   f'Já existe um produto chamado "{dados["nome"]}".')
            return
        self.carregar()

    def editar(self):
        if not self._exige_modo_gerente():
            return
        produto = self._selecionado()
        if produto is None:
            return

        dados = DialogoProduto(self.app, repositorio.categorias(), produto).aguardar()
        if not dados:
            return
        try:
            repositorio.atualizar_produto(produto["id"], **dados)
        except sqlite3.IntegrityError:
            messagebox.showwarning("Produto repetido",
                                   f'Já existe um produto chamado "{dados["nome"]}".')
            return
        self.carregar()

    def desativar(self):
        if not self._exige_modo_gerente():
            return
        produto = self._selecionado()
        if produto is None:
            return
        if messagebox.askyesno("Remover do cardápio",
                               f'Remover "{produto["nome"]}" do cardápio?'):
            repositorio.desativar_produto(produto["id"])
            self.carregar()
