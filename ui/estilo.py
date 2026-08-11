"""
Tema visual da aplicação.

Escolhas pensadas em quem vai usar (atendente com fila no balcão):
fonte grande, botões largos, cores fortes para as ações principais e
contraste alto — nada de cinza sobre cinza.
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

CORES = {
    "fundo": "#EEF1F5",
    "painel": "#FFFFFF",
    "menu": "#12263A",
    "menu_hover": "#1D3B5C",
    "menu_ativo": "#E8590C",
    "primaria": "#E8590C",
    "primaria_escura": "#C64A05",
    "sucesso": "#2B8A3E",
    "sucesso_escura": "#20692F",
    "perigo": "#C92A2A",
    "aviso": "#B8860B",
    "texto": "#1F2933",
    "texto_suave": "#67757F",
    "texto_claro": "#FFFFFF",
    "borda": "#D5DDE5",
    "destaque": "#FFF4E6",
}


def familia_disponivel(*preferidas: str) -> str:
    disponiveis = set(tkfont.families())
    for familia in preferidas:
        if familia in disponiveis:
            return familia
    return "TkDefaultFont"


def aplicar(raiz: tk.Tk) -> dict:
    """Configura o tema ttk e devolve o dicionário de fontes do sistema."""
    familia = familia_disponivel("Segoe UI", "Inter", "Ubuntu", "DejaVu Sans", "Helvetica")

    fontes = {
        "padrao": (familia, 11),
        "pequena": (familia, 9),
        "media": (familia, 12),
        "forte": (familia, 12, "bold"),
        "titulo": (familia, 17, "bold"),
        "subtitulo": (familia, 13, "bold"),
        "total": (familia, 26, "bold"),
        "menu": (familia, 12),
    }

    tkfont.nametofont("TkDefaultFont").configure(family=familia, size=11)
    tkfont.nametofont("TkTextFont").configure(family=familia, size=11)

    raiz.configure(bg=CORES["fundo"])

    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")

    estilo.configure(".", font=fontes["padrao"], background=CORES["fundo"],
                     foreground=CORES["texto"])
    estilo.configure("TFrame", background=CORES["fundo"])
    estilo.configure("Painel.TFrame", background=CORES["painel"])
    estilo.configure("Menu.TFrame", background=CORES["menu"])
    estilo.configure("Cabecalho.TFrame", background=CORES["menu"])

    estilo.configure("TLabel", background=CORES["fundo"], foreground=CORES["texto"])
    estilo.configure("Painel.TLabel", background=CORES["painel"])
    estilo.configure("Titulo.TLabel", background=CORES["fundo"],
                     font=fontes["titulo"], foreground=CORES["texto"])
    estilo.configure("Subtitulo.TLabel", background=CORES["painel"],
                     font=fontes["subtitulo"], foreground=CORES["texto"])
    estilo.configure("Suave.TLabel", background=CORES["painel"],
                     font=fontes["pequena"], foreground=CORES["texto_suave"])
    estilo.configure("SuaveFundo.TLabel", background=CORES["fundo"],
                     font=fontes["pequena"], foreground=CORES["texto_suave"])
    estilo.configure("CabecalhoTitulo.TLabel", background=CORES["menu"],
                     foreground=CORES["texto_claro"], font=fontes["subtitulo"])
    estilo.configure("CabecalhoInfo.TLabel", background=CORES["menu"],
                     foreground="#B7C4D2", font=fontes["padrao"])
    estilo.configure("Total.TLabel", background=CORES["painel"],
                     foreground=CORES["primaria"], font=fontes["total"])

    # Botões -----------------------------------------------------------------
    estilo.configure("TButton", font=fontes["padrao"], padding=(12, 8),
                     background="#E2E8EF", foreground=CORES["texto"],
                     borderwidth=0, focuscolor=CORES["fundo"])
    estilo.map("TButton", background=[("active", "#CFD8E2"), ("disabled", "#EDEFF2")],
               foreground=[("disabled", "#A5AEB7")])

    estilo.configure("Primario.TButton", font=fontes["forte"], padding=(16, 12),
                     background=CORES["primaria"], foreground=CORES["texto_claro"])
    estilo.map("Primario.TButton",
               background=[("active", CORES["primaria_escura"]), ("disabled", "#E4C4AC")])

    estilo.configure("Sucesso.TButton", font=fontes["forte"], padding=(16, 14),
                     background=CORES["sucesso"], foreground=CORES["texto_claro"])
    estilo.map("Sucesso.TButton",
               background=[("active", CORES["sucesso_escura"]), ("disabled", "#AFC9B5")])

    estilo.configure("Perigo.TButton", padding=(12, 8),
                     background=CORES["perigo"], foreground=CORES["texto_claro"])
    estilo.map("Perigo.TButton", background=[("active", "#A61E1E")])

    estilo.configure("Menu.TButton", font=fontes["menu"], padding=(16, 14),
                     background=CORES["menu"], foreground="#C9D6E2",
                     anchor="w", borderwidth=0)
    estilo.map("Menu.TButton",
               background=[("active", CORES["menu_hover"])],
               foreground=[("active", CORES["texto_claro"])])

    estilo.configure("MenuAtivo.TButton", font=(familia, 12, "bold"), padding=(16, 14),
                     background=CORES["menu_ativo"], foreground=CORES["texto_claro"],
                     anchor="w", borderwidth=0)
    estilo.map("MenuAtivo.TButton", background=[("active", CORES["primaria_escura"])])

    # Campos -----------------------------------------------------------------
    estilo.configure("TEntry", padding=8, fieldbackground="#FFFFFF",
                     bordercolor=CORES["borda"], lightcolor=CORES["borda"],
                     darkcolor=CORES["borda"])
    estilo.configure("Busca.TEntry", padding=10)
    estilo.configure("TCombobox", padding=7, arrowsize=16)
    estilo.map("TCombobox",
               fieldbackground=[("readonly", "#FFFFFF"), ("disabled", "#F1F3F5")],
               background=[("readonly", "#FFFFFF")],
               selectbackground=[("readonly", "#FFFFFF")],
               selectforeground=[("readonly", CORES["texto"])])
    estilo.configure("TSpinbox", padding=7, arrowsize=16)

    # Tabelas ----------------------------------------------------------------
    estilo.configure("Treeview", font=(familia, 10), rowheight=28,
                     background=CORES["painel"], fieldbackground=CORES["painel"],
                     borderwidth=0)
    estilo.configure("Treeview.Heading", font=(familia, 10, "bold"),
                     background="#DCE3EB", foreground=CORES["texto"],
                     padding=8, relief="flat")
    estilo.map("Treeview.Heading", background=[("active", "#CBD5E0")])
    estilo.map("Treeview", background=[("selected", CORES["primaria"])],
               foreground=[("selected", CORES["texto_claro"])])

    estilo.configure("TNotebook", background=CORES["fundo"], borderwidth=0)
    estilo.configure("TNotebook.Tab", padding=(16, 10), font=fontes["padrao"])

    estilo.configure("TLabelframe", background=CORES["painel"], bordercolor=CORES["borda"])
    estilo.configure("TLabelframe.Label", background=CORES["painel"],
                     font=fontes["forte"], foreground=CORES["texto"])

    estilo.configure("TSeparator", background=CORES["borda"])

    return fontes
