# Usa SQLite.
import sqlite3
from pathlib import Path

from flask import g

APP_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = APP_ROOT / "database" / "bugbite.sqlite"

# Este arquivo conecta a aplicação ao banco SQLite.

# `g` é um objeto especial, único por requisição, usado para armazenar
# dados que podem ser acessados por várias funções durante o request.
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE_PATH,
            detect_types= sqlite3.PARSE_DECLTYPES
        )
        # Retorna linhas que se comportam como dicionários e permitem acesso por nome da coluna.
        g.db.row_factory = sqlite3.Row

    return g.db

# Fecha a conexão, caso ela tenha sido criada.
def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

# Registra o fechamento do banco no ciclo de vida da aplicação.
def init_app(app):
    # `teardown_appcontext` chama essa função ao limpar o contexto depois da resposta.
    app.teardown_appcontext(close_db)
