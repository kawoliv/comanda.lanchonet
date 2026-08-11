"""
Sistema de Caixa para Lanchonete
Ponto de entrada da aplicação.

Uso:
    python app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import db  # noqa: E402


def main() -> None:
    db.inicializar()  # cria o banco e as tabelas na primeira execução

    from ui.janela import Aplicacao  # importado depois do banco existir

    Aplicacao().mainloop()


if __name__ == "__main__":
    main()
