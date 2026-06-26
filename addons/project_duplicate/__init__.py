import psycopg2
from odoo import tools
from odoo.tools import SQL
from odoo.exceptions import UserError
from . import models
from . import wizard

MISSING_PGVECTOR_LOG_MESSAGE = """\
PostgreSQL extension 'vector' is required to enable duplicate task detection.
More information at https://github.com/pgvector/pgvector.
"""


def pgvector_is_available(env):
    try:
        with tools.mute_logger('odoo.sql_db'), env.cr.savepoint():
            env.cr.execute(
                SQL("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            pg_vector = env.cr.fetchone()
            if not pg_vector:
                env.cr.execute(
                    SQL("CREATE EXTENSION IF NOT EXISTS vector"))
    except psycopg2.errors.FeatureNotSupported:
        raise UserError(MISSING_PGVECTOR_LOG_MESSAGE)


def _pre_init_hook(env):
    pgvector_is_available(env)


def post_init_hook(env):
    """
    Idempotent post init hook to create the vector column and construct the HNSW index.
    """
    # Check if column is already vector
    env.cr.execute("""
        SELECT udt_name FROM information_schema.columns
        WHERE table_name = 'project_task_embedding' AND column_name = 'embedding';
    """)
    res = env.cr.fetchone()
    if res and res[0] != 'vector':
        env.cr.execute("ALTER TABLE project_task_embedding DROP COLUMN embedding;")
        env.cr.execute("ALTER TABLE project_task_embedding ADD COLUMN embedding vector(384);")
    elif not res:
        env.cr.execute("ALTER TABLE project_task_embedding ADD COLUMN embedding vector(384);")

    env.cr.execute("""
        CREATE INDEX IF NOT EXISTS project_task_embedding_hnsw_idx
        ON project_task_embedding USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)
