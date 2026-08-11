"""Janela principal: cabeçalho de status, menu lateral e troca de telas."""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from core import repositorio, servicos
from core.moeda import formatar
from ui import estilo
from ui.componentes import DialogoAbrirCaixa, DialogoOperador
from ui.estilo import CORES
from ui.tela_equipe import TelaEquipe
from ui.tela_fechamento import TelaFechamento
from ui.tela_historico import TelaHistorico
from ui.tela_pdv import TelaPDV
from ui.tela_produtos import TelaProdutos

MENU = [
    ("pdv", "  Vender", TelaPDV),
    ("fechamento", "  Caixa do dia", TelaFechamento),
    ("historico", "  Histórico", TelaHistorico),
    ("produtos", "  Cardápio", TelaProdutos),
    ("equipe", "  Equipe", TelaEquipe),
]


class Aplicacao(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Caixa — Lanchonete")
        self.minsize(1180, 700)
        self._dimensionar()

        self.fontes = estilo.aplicar(self)
        self.operador = None
        self.telas = {}
        self.botoes_menu = {}
        self.tela_atual = None

        self._montar_cabecalho()
        self._montar_corpo()
        self._atalhos()

        self.after(100, self._iniciar_turno)
        self._relogio()

    # ------------------------------------------------------------------ #
    # Estrutura
    # ------------------------------------------------------------------ #

    def _dimensionar(self):
        """Abre maximizado; se o sistema não permitir, usa o tamanho da tela."""
        largura = min(1360, self.winfo_screenwidth() - 40)
        altura = min(820, self.winfo_screenheight() - 60)
        self.geometry(f"{largura}x{altura}+20+20")
        try:
            self.state("zoomed")            # Windows
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)   # Linux
            except tk.TclError:
                pass

    def _montar_cabecalho(self):
        cabecalho = tk.Frame(self, bg=CORES["menu"], height=64)
        cabecalho.pack(fill="x")
        cabecalho.pack_propagate(False)

        tk.Label(cabecalho, text="  Lanchonete · Caixa", bg=CORES["menu"],
                 fg=CORES["texto_claro"], font=self.fontes["subtitulo"]).pack(side="left", padx=16)

        self.selo_status = tk.Label(cabecalho, text="", bg=CORES["perigo"],
                                    fg=CORES["texto_claro"],
                                    font=(self.fontes["padrao"][0], 10, "bold"), padx=12, pady=4)
        self.selo_status.pack(side="left", padx=8)

        # Os itens da direita são empacotados antes para não serem espremidos
        # pelo rótulo de total, que ocupa o espaço que sobrar.
        self.rotulo_relogio = tk.Label(cabecalho, text="", bg=CORES["menu"], fg="#B7C4D2",
                                       font=self.fontes["padrao"])
        self.rotulo_relogio.pack(side="right", padx=(8, 16))

        self.botao_operador = ttk.Button(cabecalho, text="Operador", command=self.trocar_operador)
        self.botao_operador.pack(side="right", padx=6, pady=12)

        self.botao_caixa = ttk.Button(cabecalho, text="Abrir caixa", style="Primario.TButton",
                                      command=self.abrir_caixa)
        self.botao_caixa.pack(side="right", padx=6, pady=12)

        self.rotulo_total_dia = tk.Label(cabecalho, text="", bg=CORES["menu"], fg="#9FE0AE",
                                         font=(self.fontes["padrao"][0], 12, "bold"),
                                         anchor="w")
        self.rotulo_total_dia.pack(side="left", padx=14)

    def _montar_corpo(self):
        corpo = ttk.Frame(self)
        corpo.pack(fill="both", expand=True)

        menu = tk.Frame(corpo, bg=CORES["menu"], width=190)
        menu.pack(side="left", fill="y")
        menu.pack_propagate(False)

        for chave, texto, _ in MENU:
            botao = ttk.Button(menu, text=texto, style="Menu.TButton",
                               command=lambda c=chave: self.mostrar(c))
            botao.pack(fill="x")
            self.botoes_menu[chave] = botao

        tk.Label(menu, text="v1.0", bg=CORES["menu"], fg="#5A6B7D",
                 font=self.fontes["pequena"]).pack(side="bottom", pady=12)

        self.conteudo = ttk.Frame(corpo, padding=(16, 12))
        self.conteudo.pack(side="left", fill="both", expand=True)

    def _atalhos(self):
        self.bind("<F2>", lambda _: self._acao_f2())
        self.bind("<F5>", lambda _: self.mostrar("pdv"))
        self.bind("<F8>", lambda _: self.mostrar("fechamento"))
        self.bind("<F9>", lambda _: self.mostrar("historico"))
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)

    def _acao_f2(self):
        if self.tela_atual == "pdv":
            self.telas["pdv"].finalizar_venda()

    # ------------------------------------------------------------------ #
    # Navegação
    # ------------------------------------------------------------------ #

    def mostrar(self, chave: str):
        if chave not in self.telas:
            classe = dict((c, t) for c, _, t in MENU)[chave]
            self.telas[chave] = classe(self.conteudo, self)

        for widget in self.conteudo.winfo_children():
            widget.pack_forget()

        tela = self.telas[chave]
        tela.pack(fill="both", expand=True)
        tela.ao_exibir()

        self.tela_atual = chave
        for nome, botao in self.botoes_menu.items():
            botao.configure(style="MenuAtivo.TButton" if nome == chave else "Menu.TButton")

    # ------------------------------------------------------------------ #
    # Turno e caixa
    # ------------------------------------------------------------------ #

    def _iniciar_turno(self):
        funcionarios = repositorio.listar_funcionarios()
        if not funcionarios:
            messagebox.showwarning("Sem funcionários",
                                   "Cadastre ao menos um funcionário para usar o sistema.")
            self.operador = None
            self.mostrar("equipe")
            return

        escolhido = DialogoOperador(self, funcionarios).aguardar()
        self.operador = escolhido or funcionarios[0]

        self.atualizar_cabecalho()
        self.mostrar("pdv" if servicos.caixa_aberto() else "fechamento")

    def trocar_operador(self):
        funcionarios = repositorio.listar_funcionarios()
        if not funcionarios:
            return
        atual = self.operador["nome"] if self.operador else None
        escolhido = DialogoOperador(self, funcionarios, atual).aguardar()
        if escolhido:
            self.operador = escolhido
            self.atualizar_cabecalho()
            if self.tela_atual:
                self.telas[self.tela_atual].ao_exibir()

    def abrir_caixa(self):
        if servicos.caixa_aberto():
            self.mostrar("fechamento")
            return

        funcionarios = repositorio.listar_funcionarios()
        if not funcionarios:
            messagebox.showwarning("Sem funcionários", "Cadastre um funcionário primeiro.")
            return

        atual = self.operador["nome"] if self.operador else None
        dados = DialogoAbrirCaixa(self, funcionarios, atual).aguardar()
        if not dados:
            return

        try:
            servicos.abrir_caixa(dados["funcionario_id"], dados["valor_centavos"])
        except servicos.ErroDeNegocio as erro:
            messagebox.showwarning("Não foi possível abrir", str(erro))
            return

        self.atualizar_cabecalho()
        self.mostrar("pdv")

    def atualizar_cabecalho(self):
        caixa = servicos.caixa_aberto()

        if caixa:
            resumo = servicos.resumo_caixa(caixa["id"])
            self.selo_status.configure(text=f"CAIXA ABERTO  ·  Nº {caixa['id']}",
                                       bg=CORES["sucesso"])
            self.rotulo_total_dia.configure(
                text=f"Hoje: {formatar(resumo['total_centavos'])}"
            )
            self.botao_caixa.configure(text="Fechar caixa",
                                       command=lambda: self.mostrar("fechamento"))
        else:
            self.selo_status.configure(text="CAIXA FECHADO", bg=CORES["perigo"])
            self.rotulo_total_dia.configure(text="")
            self.botao_caixa.configure(text="Abrir caixa", command=self.abrir_caixa)

        if self.operador:
            self.botao_operador.configure(text=f"Operador: {self.operador['nome']}")

    def _relogio(self):
        self.rotulo_relogio.configure(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.after(1000, self._relogio)

    def ao_fechar(self):
        if servicos.caixa_aberto():
            sair = messagebox.askyesno(
                "Sair",
                "O caixa ainda está ABERTO.\n\n"
                "Se sair agora, ele continuará aberto e você poderá retomar depois.\n"
                "Deseja sair mesmo assim?",
            )
            if not sair:
                return
        self.destroy()
