"""SQL string utilities.

Pure Python SQL helpers with no Odoo dependencies.
These utilities work with SQL strings and don't require a database connection.
"""

__all__ = [
    "escape_psql",
    "make_identifier",
    "make_index_name",
    "pg_varchar",
    "reverse_order",
]

from binascii import crc32


def escape_psql(to_escape: str) -> str:
    r"""Escape special characters for PostgreSQL LIKE patterns.

    Escapes backslash, percent, and underscore characters which have
    special meaning in LIKE patterns.

    :param to_escape: The string to escape
    :returns: The escaped string

    Example::

        >>> escape_psql('10%_off')
        '10\\\\%\\\\_off'
    """
    return to_escape.replace("\\", r"\\").replace("%", r"\%").replace("_", r"\_")


def pg_varchar(size: int = 0) -> str:
    """Return the VARCHAR declaration for the provided size.

    :param size: VARCHAR size (0 or negative for unlimited)
    :returns: 'VARCHAR(n)' for positive size, 'VARCHAR' otherwise
    :raises ValueError: If size is not an integer

    Example::

        >>> pg_varchar(255)
        'VARCHAR(255)'
        >>> pg_varchar()
        'VARCHAR'
        >>> pg_varchar(0)
        'VARCHAR'
    """
    if size:
        if not isinstance(size, int):
            raise ValueError(f"VARCHAR parameter should be an int, got {type(size)}")
        if size > 0:
            return f"VARCHAR({size})"
    return "VARCHAR"


def reverse_order(order: str) -> str:
    """Reverse an ORDER BY clause.

    Changes ASC to DESC and vice versa for each column in the order clause.

    :param order: An ORDER BY clause (without the 'ORDER BY' keywords)
    :returns: The reversed order clause

    Example::

        >>> reverse_order('name asc, date desc')
        'name desc, date asc'
        >>> reverse_order('id')
        'id desc'
    """
    items = []
    for item in order.split(","):
        item = item.lower().split()
        direction = "asc" if item[1:] == ["desc"] else "desc"
        items.append(f"{item[0]} {direction}")
    return ", ".join(items)


def make_identifier(identifier: str) -> str:
    """Return identifier, possibly modified to fit PostgreSQL's limit.

    PostgreSQL identifiers are limited to 63 characters. If the identifier
    is too long, it's truncated and padded with a CRC32 hash to maintain
    uniqueness.

    :param identifier: The identifier to process
    :returns: The (possibly truncated) identifier

    Example::

        >>> make_identifier('short_name')
        'short_name'
        >>> len(make_identifier('a' * 100))
        63
    """
    if len(identifier) > 63:
        return f"{identifier[:54]}_{crc32(identifier.encode()):08x}"
    return identifier


def make_index_name(table_name: str, column_name: str) -> str:
    """Return an index name according to PostgreSQL conventions.

    :param table_name: The table name
    :param column_name: The column name
    :returns: An index name in the format '{table}__{column}_index'

    Example::

        >>> make_index_name('res_partner', 'email')
        'res_partner__email_index'
    """
    return make_identifier(f"{table_name}__{column_name}_index")
