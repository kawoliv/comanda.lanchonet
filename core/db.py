"""
Conexão e esquema do banco de dados (SQLite).

O SQLite foi escolhido porque o sistema roda no próprio computador do balcão:
sem servidor, sem internet, sem instalação extra. O banco inteiro é um arquivo
em dados/caixa.db, o que também facilita o backup (basta copiar o arquivo).
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

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
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL UNIQUE,
    cargo     TEXT    NOT NULL DEFAULT 'Atendente',
    ativo     INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

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

FUNCIONARIOS_INICIAIS = [
    ("Gerente", "Gerente"),
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


def inicializar() -> None:
    """Cria as tabelas (se ainda não existirem) e popula o cadastro básico."""
    PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)

    with transacao() as con:
        con.executescript(ESQUEMA)

        if con.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO funcionarios (nome, cargo) VALUES (?, ?)",
                FUNCIONARIOS_INICIAIS,
            )

        if con.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO produtos (nome, categoria, preco_centavos) VALUES (?, ?, ?)",
                PRODUTOS_INICIAIS,
            )
