"""
Conexão e esquema do banco de dados (SQLite).

O SQLite foi escolhido porque o sistema roda no próprio computador do balcão:
sem servidor, sem internet, sem instalação extra. O banco inteiro é um arquivo
em dados/caixa.db, o que também facilita o backup (basta copiar o arquivo).
"""

import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

from core import auth

# Empacotado com PyInstaller (--onefile), __file__ aponta para a pasta
# temporária de extração (_MEIPASS), que é apagada a cada execução. Nesse
# caso usamos a pasta do .exe para que dados/ e relatorios/ persistam.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

PASTA_DADOS = BASE_DIR / "dados"
PASTA_RELATORIOS = BASE_DIR / "relatorios"


def caminho_banco() -> Path:
    """Caminho do arquivo .db (a variável CAIXA_DB permite apontar para outro)."""
    personalizado = os.environ.get("CAIXA_DB")
    return Path(personalizado) if personalizado else PASTA_DADOS / "caixa.db"


def conectar() -> sqlite3.Connection:
    caminho = caminho_banco()
    caminho.parent.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row          # devolve linhas acessíveis por nome
    conexao.execute("PRAGMA foreign_keys = ON")  # SQLite exige ligar isso por conexão
    return conexao


@contextmanager
def transacao():
    """
    Abre conexão, faz commit no fim e rollback se der erro.

        with transacao() as con:
            con.execute("INSERT ...")
    """
    conexao = conectar()
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


ESQUEMA = """
CREATE TABLE IF NOT EXISTS funcionarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT    NOT NULL UNIQUE,
    cargo      TEXT    NOT NULL DEFAULT 'Atendente',
    login      TEXT,                      -- só preenchido para o cargo Gerente
    senha_hash TEXT,                      -- PBKDF2, ver core/auth.py
    ativo      INTEGER NOT NULL DEFAULT 1,
    criado_em  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Login não pode repetir entre funcionários, mas vários podem não ter login
-- (índice parcial ignora as linhas com login NULL).
CREATE UNIQUE INDEX IF NOT EXISTS idx_funcionarios_login
    ON funcionarios (login) WHERE login IS NOT NULL;

CREATE TABLE IF NOT EXISTS produtos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    categoria      TEXT    NOT NULL DEFAULT 'Geral',
    preco_centavos INTEGER NOT NULL CHECK (preco_centavos >= 0),
    ativo          INTEGER NOT NULL DEFAULT 1,
    criado_em      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS caixas (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    data_operacao             TEXT    NOT NULL,              -- AAAA-MM-DD
    aberto_em                 TEXT    NOT NULL,
    fechado_em                TEXT,
    funcionario_abertura_id   INTEGER NOT NULL REFERENCES funcionarios(id),
    funcionario_fechamento_id INTEGER          REFERENCES funcionarios(id),
    valor_abertura_centavos   INTEGER NOT NULL DEFAULT 0,    -- troco inicial
    valor_contado_centavos    INTEGER,                       -- dinheiro conferido na gaveta
    diferenca_centavos        INTEGER,                       -- contado - esperado
    status                    TEXT    NOT NULL DEFAULT 'ABERTO'
                                      CHECK (status IN ('ABERTO', 'FECHADO')),
    observacoes               TEXT,
    planilha                  TEXT                           -- caminho do .xlsx gerado
);

-- Índice parcial: garante NO BANCO que só existe um caixa aberto por vez.
CREATE UNIQUE INDEX IF NOT EXISTS idx_caixa_unico_aberto
    ON caixas (status) WHERE status = 'ABERTO';

CREATE TABLE IF NOT EXISTS vendas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    caixa_id            INTEGER NOT NULL REFERENCES caixas(id) ON DELETE CASCADE,
    funcionario_id      INTEGER NOT NULL REFERENCES funcionarios(id),
    data_hora           TEXT    NOT NULL,                    -- AAAA-MM-DD HH:MM:SS
    forma_pagamento     TEXT    NOT NULL DEFAULT 'Dinheiro',
    total_centavos      INTEGER NOT NULL CHECK (total_centavos >= 0),
    cancelada           INTEGER NOT NULL DEFAULT 0,
    cancelada_em        TEXT,
    motivo_cancelamento TEXT
);

CREATE INDEX IF NOT EXISTS idx_vendas_caixa ON vendas (caixa_id);
CREATE INDEX IF NOT EXISTS idx_vendas_data  ON vendas (data_hora);

-- Os itens guardam uma "fotografia" do produto (nome e preço da hora da venda).
-- Se o preço do lanche mudar amanhã, o histórico de ontem continua correto.
CREATE TABLE IF NOT EXISTS itens_venda (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id            INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
    produto_id          INTEGER          REFERENCES produtos(id),
    nome_produto        TEXT    NOT NULL,
    categoria           TEXT    NOT NULL DEFAULT 'Geral',
    quantidade          INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unit_centavos INTEGER NOT NULL,
    subtotal_centavos   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_itens_venda ON itens_venda (venda_id);
"""

# Credencial do Gerente semeada na primeira execução — troque a senha depois
# em Equipe > Editar (é o único jeito de entrar no Modo Gerente pela primeira vez).
LOGIN_GERENTE_PADRAO = "gerente"
SENHA_GERENTE_PADRAO = "gerente123"

FUNCIONARIOS_INICIAIS = [
    ("Gerente", "Gerente", LOGIN_GERENTE_PADRAO, SENHA_GERENTE_PADRAO),
]

PRODUTOS_INICIAIS = [
    ("X-Burger", "Lanches", 1800),
    ("X-Salada", "Lanches", 2000),
    ("X-Bacon", "Lanches", 2200),
    ("Misto Quente", "Lanches", 1000),
    ("Cachorro-Quente", "Lanches", 1200),
    ("Batata Frita P", "Porções", 1500),
    ("Batata Frita G", "Porções", 2500),
    ("Coca-Cola Lata", "Bebidas", 600),
    ("Guaraná Lata", "Bebidas", 600),
    ("Suco Natural 300ml", "Bebidas", 800),
    ("Água Mineral", "Bebidas", 400),
    ("Pudim", "Sobremesas", 900),
]


def _migrar_esquema(con: sqlite3.Connection) -> None:
    """Adiciona colunas novas a bancos criados por versões anteriores.

    `CREATE TABLE IF NOT EXISTS` não altera uma tabela já existente, então
    quem já tinha `dados/caixa.db` antes do login do Gerente precisa deste
    passo para ganhar as colunas `login`/`senha_hash`.
    """
    tabela_existe = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'funcionarios'"
    ).fetchone()
    if not tabela_existe:
        return

    colunas = {linha["name"] for linha in con.execute("PRAGMA table_info(funcionarios)")}
    if "login" not in colunas:
        con.execute("ALTER TABLE funcionarios ADD COLUMN login TEXT")
    if "senha_hash" not in colunas:
        con.execute("ALTER TABLE funcionarios ADD COLUMN senha_hash TEXT")

    # Sempre confere (não só quando as colunas acabaram de ser criadas): um
    # banco já migrado antes desta credencial padrão existir também precisa
    # ganhá-la — senão fica sem nenhum jeito de entrar no Modo Gerente.
    _semear_login_gerente_existente(con)


def _semear_login_gerente_existente(con: sqlite3.Connection) -> None:
    """Dá a credencial padrão ao Gerente já cadastrado num banco antigo.

    Sem isso, quem já usava o sistema antes do login existir ficaria com um
    funcionário de cargo Gerente mas sem login/senha — ninguém conseguiria
    entrar no Modo Gerente pela primeira vez.
    """
    ja_tem_login = con.execute(
        "SELECT 1 FROM funcionarios WHERE login IS NOT NULL"
    ).fetchone()
    if ja_tem_login:
        return

    gerente = con.execute(
        "SELECT id FROM funcionarios WHERE cargo = 'Gerente' ORDER BY ativo DESC, id ASC LIMIT 1"
    ).fetchone()
    if gerente is None:
        return

    con.execute(
        "UPDATE funcionarios SET login = ?, senha_hash = ? WHERE id = ?",
        (LOGIN_GERENTE_PADRAO, auth.gerar_hash_senha(SENHA_GERENTE_PADRAO), gerente["id"]),
    )


def inicializar() -> None:
    """Cria as tabelas (se ainda não existirem) e popula o cadastro básico."""
    PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)

    with transacao() as con:
        _migrar_esquema(con)
        con.executescript(ESQUEMA)

        if con.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO funcionarios (nome, cargo, login, senha_hash) VALUES (?, ?, ?, ?)",
                [
                    (nome, cargo, login, auth.gerar_hash_senha(senha))
                    for nome, cargo, login, senha in FUNCIONARIOS_INICIAIS
                ],
            )

        if con.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO produtos (nome, categoria, preco_centavos) VALUES (?, ?, ?)",
                PRODUTOS_INICIAIS,
            )
