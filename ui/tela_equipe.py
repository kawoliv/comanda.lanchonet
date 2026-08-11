"""Cadastro da equipe: quem pode aparecer como vendedor no PDV."""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from core import repositorio
from ui.componentes import DialogoFuncionario, tabela
from ui.estilo import CORES


class TelaEquipe(ttk.Frame):
    def __init__(self, pai, app):
        super().__init__(pai, style="TFrame")
        self.app = app
        self.funcionarios = {}

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 12))
        ttk.Label(barra, text="Equipe", style="Titulo.TLabel").pack(side="left")
        ttk.Button(barra, text="+  Novo funcionário", style="Primario.TButton",
                   command=self.novo).pack(side="right")

        painel = tk.Frame(self, bg=CORES["painel"], highlightbackground=CORES["borda"],
                          highlightthickness=1)
        painel.pack(fill="both", expand=True)

        interno = ttk.Frame(painel, style="Painel.TFrame", padding=16)
        interno.pack(fill="both", expand=True)

        ttk.Label(interno, text="Funcionários ativos aparecem na lista de vendedores do PDV.",
                  style="Suave.TLabel").pack(anchor="w", pady=(0, 10))

        self.lista = tabela(interno, [
            ("nome", "Nome", 320, "w"),
            ("cargo", "Cargo", 200, "w"),
        ], altura=14)
        self.lista.quadro.pack(fill="both", expand=True)
        self.lista.bind("<Double-1>", lambda _: self.editar())

        acoes = ttk.Frame(interno, style="Painel.TFrame")
        acoes.pack(fill="x", pady=(12, 0))
        ttk.Button(acoes, text="Editar", command=self.editar).pack(side="left", padx=(0, 8))
        ttk.Button(acoes, text="Desativar", style="Perigo.TButton",
                   command=self.desativar).pack(side="left")

    def ao_exibir(self):
        self.carregar()

    def carregar(self):
        self.lista.delete(*self.lista.get_children())
        self.funcionarios.clear()

        for funcionario in repositorio.listar_funcionarios():
            iid = self.lista.insert("", "end",
                                    values=(funcionario["nome"], funcionario["cargo"]))
            self.funcionarios[iid] = funcionario

    def _selecionado(self):
        selecao = self.lista.selection()
        if not selecao:
            messagebox.showinfo("Selecione", "Escolha um funcionário na lista.")
            return None
        return self.funcionarios[selecao[0]]

    def novo(self):
        dados = DialogoFuncionario(self.app).aguardar()
        if not dados:
            return
        try:
            repositorio.criar_funcionario(**dados)
        except sqlite3.IntegrityError:
            messagebox.showwarning("Nome repetido",
                                   f'Já existe um funcionário chamado "{dados["nome"]}".')
            return
        self.carregar()

    def editar(self):
        funcionario = self._selecionado()
        if funcionario is None:
            return

        dados = DialogoFuncionario(self.app, funcionario).aguardar()
        if not dados:
            return
        try:
            repositorio.atualizar_funcionario(funcionario["id"], **dados)
        except sqlite3.IntegrityError:
            messagebox.showwarning("Nome repetido",
                                   f'Já existe um funcionário chamado "{dados["nome"]}".')
            return
        self.carregar()
        self.app.atualizar_cabecalho()

    def desativar(self):
        funcionario = self._selecionado()
        if funcionario is None:
            return
        if len(repositorio.listar_funcionarios()) <= 1:
            messagebox.showwarning("Não é possível",
                                   "É preciso manter pelo menos um funcionário ativo.")
            return
        if messagebox.askyesno("Desativar", f'Desativar "{funcionario["nome"]}"?\n\n'
                                            "As vendas já registradas continuam no histórico."):
            repositorio.desativar_funcionario(funcionario["id"])
            self.carregar()
