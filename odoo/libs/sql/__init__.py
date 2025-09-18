"""SQL string utilities.

Pure Python SQL helpers with no Odoo dependencies.
"""

from .utils import (
    escape_psql,
    pg_varchar,
    reverse_order,
    make_identifier,
    make_index_name,
)

__all__ = [
    "escape_psql",
    "make_identifier",
    "make_index_name",
    "pg_varchar",
    "reverse_order",
]
