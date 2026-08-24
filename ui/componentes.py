"""Widgets reutilizáveis e janelas de diálogo."""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from core import servicos
from core.moeda import ValorInvalido, formatar, para_centavos
from ui.estilo import CORES


def abrir_no_sistema(caminho) -> bool:
    """Abre a planilha (ou a pasta) no programa padrão do sistema operacional."""
    caminho = Path(caminho)
    if not caminho.exists():
        return False
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho)  # noqa: S606 - API padrão do Windows
        elif sys.platform == "darwin":
            subprocess.run(["open", str(caminho)], check=False)
        else:
            subprocess.run(["xdg-open", str(caminho)], check=False)
        return True
    except OSError:
        return False


def cartao_indicador(pai, titulo: str, valor: str, cor: str = None) -> dict:
    """Cartão branco com um número em destaque (usado nos resumos)."""
    quadro = tk.Frame(pai, bg=CORES["painel"], highlightbackground=CORES["borda"],
                      highlightthickness=1)
    tk.Label(quadro, text=titulo.upper(), bg=CORES["painel"], fg=CORES["texto_suave"],
             font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
    rotulo_valor = tk.Label(quadro, text=valor, bg=CORES["painel"],
                            fg=cor or CORES["texto"], font=("TkDefaultFont", 18, "bold"))
    rotulo_valor.pack(anchor="w", padx=14, pady=(2, 12))
    return {"quadro": quadro, "valor": rotulo_valor}


def tabela(pai, colunas: list, alturas: dict = None, altura: int = 12) -> ttk.Treeview:
    """
    Treeview com barra de rolagem já montada.

    `colunas` = [(chave, título, largura, âncora), ...]
    """
    quadro = ttk.Frame(pai, style="Painel.TFrame")
    chaves = [coluna[0] for coluna in colunas]

    arvore = ttk.Treeview(quadro, columns=chaves, show="headings", height=altura,
                          selectmode="browse")
    for chave, titulo, largura, ancora in colunas:
        arvore.heading(chave, text=titulo)
        arvore.column(chave, width=largura, anchor=ancora, stretch=(ancora == "w"))

    rolagem = ttk.Scrollbar(quadro, orient="vertical", command=arvore.yview)
    arvore.configure(yscrollcommand=rolagem.set)

    arvore.pack(side="left", fill="both", expand=True)
    rolagem.pack(side="right", fill="y")

    arvore.quadro = quadro  # atalho para posicionar o conjunto
    return arvore


class Dialogo(tk.Toplevel):
    """Base para as janelas modais do sistema."""

    def __init__(self, pai, titulo: str, largura: int = 460, altura: int = 320):
        super().__init__(pai)
        self.resultado = None

        self.title(titulo)
        self.configure(bg=CORES["painel"])
        self.resizable(False, False)
        self.transient(pai)

        self.corpo = ttk.Frame(self, style="Painel.TFrame", padding=24)
        self.corpo.pack(fill="both", expand=True)

        ttk.Label(self.corpo, text=titulo, style="Subtitulo.TLabel").pack(anchor="w")
        ttk.Separator(self.corpo).pack(fill="x", pady=(10, 16))

        self.centralizar(pai, largura, altura)
        self.bind("<Escape>", lambda _: self.destroy())

    def centralizar(self, pai, largura, altura):
        self.update_idletasks()
        x = pai.winfo_rootx() + (pai.winfo_width() - largura) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - altura) // 3
        self.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")

    def aguardar(self):
        self.grab_set()
        self.wait_window()
        return self.resultado

    def rodape(self, texto_confirmar: str, ao_confirmar, estilo: str = "Primario.TButton"):
        barra = ttk.Frame(self.corpo, style="Painel.TFrame")
        barra.pack(side="bottom", fill="x", pady=(18, 0))
        ttk.Button(barra, text="Cancelar", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(barra, text=texto_confirmar, style=estilo,
                   command=ao_confirmar).pack(side="right")
        self.bind("<Return>", lambda _: ao_confirmar())


class DialogoAbrirCaixa(Dialogo):
    """Pergunta quem está abrindo o caixa e quanto tem de troco inicial."""

    def __init__(self, pai, funcionarios: list, operador_atual=None):
        super().__init__(pai, "Abertura de caixa", 480, 360)
        self.funcionarios = funcionarios

        ttk.Label(self.corpo, text="Responsável pela abertura",
                  style="Painel.TLabel").pack(anchor="w")
        self.combo_funcionario = ttk.Combobox(
            self.corpo, state="readonly", font=("TkDefaultFont", 12),
            values=[f["nome"] for f in funcionarios],
        )
        self.combo_funcionario.pack(fill="x", pady=(4, 16), ipady=4)
        if funcionarios:
            indice = 0
            if operador_atual:
                nomes = [f["nome"] for f in funcionarios]
                if operador_atual in nomes:
                    indice = nomes.index(operador_atual)
            self.combo_funcionario.current(indice)

        ttk.Label(self.corpo, text="Troco inicial na gaveta (R$)",
                  style="Painel.TLabel").pack(anchor="w")
        self.campo_valor = ttk.Entry(self.corpo, font=("TkDefaultFont", 14))
        self.campo_valor.pack(fill="x", pady=(4, 6), ipady=6)
        self.campo_valor.insert(0, "0,00")
        self.campo_valor.select_range(0, "end")

        ttk.Label(self.corpo, text="Dinheiro deixado no caixa para dar troco. "
                                   "Use 0,00 se não houver.",
                  style="Suave.TLabel", wraplength=400).pack(anchor="w")

        self.erro = ttk.Label(self.corpo, text="", style="Suave.TLabel", foreground=CORES["perigo"])
        self.erro.pack(anchor="w", pady=(10, 0))

        self.rodape("Abrir caixa", self.confirmar, "Sucesso.TButton")
        self.campo_valor.focus_set()

    def confirmar(self):
        if not self.combo_funcionario.get():
            self.erro.configure(text="Selecione o responsável.")
            return
        try:
            centavos = para_centavos(self.campo_valor.get())
        except ValorInvalido as erro:
            self.erro.configure(text=str(erro))
            return

        funcionario = self.funcionarios[self.combo_funcionario.current()]
        self.resultado = {"funcionario_id": funcionario["id"],
                          "nome": funcionario["nome"],
                          "valor_centavos": centavos}
        self.destroy()


class DialogoOperador(Dialogo):
    """Pergunta quem está usando o sistema neste turno."""

    def __init__(self, pai, funcionarios: list, atual: str = None):
        super().__init__(pai, "Quem está no caixa?", 440, 280)
        self.funcionarios = funcionarios

        ttk.Label(self.corpo,
                  text="O nome escolhido aparece como vendedor padrão nas vendas.",
                  style="Suave.TLabel", wraplength=380).pack(anchor="w", pady=(0, 12))

        self.combo = ttk.Combobox(self.corpo, state="readonly", font=("TkDefaultFont", 13),
                                  values=[f["nome"] for f in funcionarios])
        self.combo.pack(fill="x", ipady=6)

        nomes = [f["nome"] for f in funcionarios]
        self.combo.current(nomes.index(atual) if atual in nomes else 0)

        self.rodape("Entrar", self.confirmar)
        self.combo.focus_set()

    def confirmar(self):
        self.resultado = self.funcionarios[self.combo.current()]
        self.destroy()


class DialogoProduto(Dialogo):
    """Cadastro e edição de produto."""

    def __init__(self, pai, categorias: list, produto=None):
        titulo = "Editar produto" if produto else "Novo produto"
        super().__init__(pai, titulo, 480, 400)

        ttk.Label(self.corpo, text="Nome do produto", style="Painel.TLabel").pack(anchor="w")
        self.campo_nome = ttk.Entry(self.corpo, font=("TkDefaultFont", 12))
        self.campo_nome.pack(fill="x", pady=(4, 14), ipady=4)

        ttk.Label(self.corpo, text="Categoria", style="Painel.TLabel").pack(anchor="w")
        self.combo_categoria = ttk.Combobox(self.corpo, values=categorias,
                                            font=("TkDefaultFont", 12))
        self.combo_categoria.pack(fill="x", pady=(4, 14), ipady=4)

        ttk.Label(self.corpo, text="Preço de venda (R$)", style="Painel.TLabel").pack(anchor="w")
        self.campo_preco = ttk.Entry(self.corpo, font=("TkDefaultFont", 14))
        self.campo_preco.pack(fill="x", pady=(4, 6), ipady=6)

        self.erro = ttk.Label(self.corpo, text="", style="Suave.TLabel", foreground=CORES["perigo"])
        self.erro.pack(anchor="w", pady=(8, 0))

        if produto:
            self.campo_nome.insert(0, produto["nome"])
            self.combo_categoria.set(produto["categoria"])
            self.campo_preco.insert(0, formatar(produto["preco_centavos"]).replace("R$ ", ""))
        else:
            self.combo_categoria.set(categorias[0] if categorias else "Geral")
            self.campo_preco.insert(0, "0,00")

        self.rodape("Salvar", self.confirmar)
        self.campo_nome.focus_set()

    def confirmar(self):
        nome = self.campo_nome.get().strip()
        if not nome:
            self.erro.configure(text="Informe o nome do produto.")
            return
        try:
            preco = para_centavos(self.campo_preco.get())
        except ValorInvalido as erro:
            self.erro.configure(text=str(erro))
            return
        if preco <= 0:
            self.erro.configure(text="O preço deve ser maior que zero.")
            return

        self.resultado = {"nome": nome,
                          "categoria": self.combo_categoria.get().strip() or "Geral",
                          "preco_centavos": preco}
        self.destroy()


class DialogoFuncionario(Dialogo):
    """Cadastro e edição de funcionário.

    Login e senha só aparecem quando o cargo é "Gerente" — são eles que dão
    acesso ao Modo Gerente (ver DialogoLoginGerente e ui/janela.py).
    """

    CARGOS = ["Atendente", "Caixa", "Cozinha", "Gerente"]

    def __init__(self, pai, funcionario=None):
        titulo = "Editar funcionário" if funcionario else "Novo funcionário"
        super().__init__(pai, titulo, 480, 560)
        self.editando = funcionario is not None

        ttk.Label(self.corpo, text="Nome", style="Painel.TLabel").pack(anchor="w")
        self.campo_nome = ttk.Entry(self.corpo, font=("TkDefaultFont", 12))
        self.campo_nome.pack(fill="x", pady=(4, 14), ipady=4)

        ttk.Label(self.corpo, text="Cargo", style="Painel.TLabel").pack(anchor="w")
        self.combo_cargo = ttk.Combobox(self.corpo, values=self.CARGOS,
                                        font=("TkDefaultFont", 12))
        self.combo_cargo.pack(fill="x", pady=(4, 6), ipady=4)
        self.combo_cargo.bind("<<ComboboxSelected>>", lambda _: self._atualizar_campos_gerente())
        self.combo_cargo.bind("<KeyRelease>", lambda _: self._atualizar_campos_gerente())

        self.quadro_gerente = ttk.Frame(self.corpo, style="Painel.TFrame")

        ttk.Label(self.quadro_gerente, text="Login de acesso administrativo",
                  style="Painel.TLabel").pack(anchor="w")
        self.campo_login = ttk.Entry(self.quadro_gerente, font=("TkDefaultFont", 12))
        self.campo_login.pack(fill="x", pady=(4, 14), ipady=4)

        texto_senha = "Nova senha (deixe em branco para manter a atual)" if self.editando else "Senha"
        ttk.Label(self.quadro_gerente, text=texto_senha, style="Painel.TLabel",
                  wraplength=420).pack(anchor="w")
        self.campo_senha = ttk.Entry(self.quadro_gerente, font=("TkDefaultFont", 12), show="•")
        self.campo_senha.pack(fill="x", pady=(4, 6), ipady=4)

        self.erro = ttk.Label(self.corpo, text="", style="Suave.TLabel", foreground=CORES["perigo"])
        self.erro.pack(anchor="w", pady=(8, 0))

        if funcionario:
            self.campo_nome.insert(0, funcionario["nome"])
            self.combo_cargo.set(funcionario["cargo"])
            if funcionario["login"]:
                self.campo_login.insert(0, funcionario["login"])
        else:
            self.combo_cargo.set("Atendente")

        self._atualizar_campos_gerente()
        self.rodape("Salvar", self.confirmar)
        self.campo_nome.focus_set()

    def _eh_gerente(self) -> bool:
        return self.combo_cargo.get().strip().lower() == "gerente"

    def _atualizar_campos_gerente(self):
        if self._eh_gerente():
            self.quadro_gerente.pack(fill="x", pady=(0, 6))
        else:
            self.quadro_gerente.pack_forget()

    def confirmar(self):
        nome = self.campo_nome.get().strip()
        if not nome:
            self.erro.configure(text="Informe o nome do funcionário.")
            return
        self.resultado = {
            "nome": nome,
            "cargo": self.combo_cargo.get().strip() or "Atendente",
            "login": self.campo_login.get() if self._eh_gerente() else "",
            "senha": self.campo_senha.get() if self._eh_gerente() else "",
        }
        self.destroy()


class DialogoLoginGerente(Dialogo):
    """Login/senha para entrar no Modo Gerente (libera ações administrativas)."""

    def __init__(self, pai):
        super().__init__(pai, "Modo Gerente", 420, 300)

        ttk.Label(self.corpo, text="Login", style="Painel.TLabel").pack(anchor="w")
        self.campo_login = ttk.Entry(self.corpo, font=("TkDefaultFont", 13))
        self.campo_login.pack(fill="x", pady=(4, 14), ipady=5)

        ttk.Label(self.corpo, text="Senha", style="Painel.TLabel").pack(anchor="w")
        self.campo_senha = ttk.Entry(self.corpo, font=("TkDefaultFont", 13), show="•")
        self.campo_senha.pack(fill="x", pady=(4, 6), ipady=5)
        self.campo_senha.bind("<Return>", lambda _: self.confirmar())

        self.erro = ttk.Label(self.corpo, text="", style="Suave.TLabel", foreground=CORES["perigo"])
        self.erro.pack(anchor="w", pady=(8, 0))

        self.rodape("Entrar", self.confirmar, "Primario.TButton")
        self.campo_login.focus_set()

    def confirmar(self):
        try:
            self.resultado = servicos.autenticar_gerente(
                self.campo_login.get(), self.campo_senha.get()
            )
        except servicos.ErroDeNegocio as erro:
            self.erro.configure(text=str(erro))
            return
        self.destroy()
