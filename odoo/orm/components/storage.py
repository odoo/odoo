"""Storage backend protocol and implementations for the ORM.

This module provides:

* :class:`StorageBackend` — a Protocol defining the interface for record
  storage.  Enables testing without PostgreSQL.
* :class:`DictBackend` — an in-memory backend for pure-Python unit tests.

Usage::

    # In tests — no database required
    backend = DictBackend()
    ids = backend.insert_rows("res_partner", ["name", "email"],
                              [("Alice", "a@x.com"), ("Bob", "b@x.com")])
    rows = backend.fetch_rows("res_partner", ids, ["name"])

    # Search by column value (simulates WHERE clause)
    partner_ids = backend.search_rows("sale_order", "partner_id", 1)
"""

import typing
from collections import defaultdict
from operator import eq, ge, gt, le, lt, ne

# Supported comparison operators for search_rows
_OPERATORS: dict[str, typing.Callable] = {
    "=": eq,
    "!=": ne,
    "<": lt,
    "<=": le,
    ">": gt,
    ">=": ge,
    "in": lambda v, vals: v in vals,
    "not in": lambda v, vals: v not in vals,
}


class StorageBackend(typing.Protocol):
    """Protocol for record storage backends.

    Implementations must support basic CRUD operations on tables.
    The protocol is intentionally minimal — only the operations needed
    for ORM field-level caching and flushing.
    """

    def fetch_rows(self, table: str, ids: list[int], columns: list[str]) -> list[tuple]:
        """Fetch specified columns for the given record IDs.

        Returns a list of tuples in the same column order as *columns*.
        Missing IDs are silently skipped.
        """
        ...

    def insert_rows(
        self, table: str, columns: list[str], rows: list[tuple]
    ) -> list[int]:
        """Insert rows and return their new IDs."""
        ...

    def update_rows(
        self, table: str, updates: list[tuple[int, dict[str, typing.Any]]]
    ) -> None:
        """Update rows.  Each entry is ``(id, {column: value})``."""
        ...

    def delete_rows(self, table: str, ids: list[int]) -> None:
        """Delete rows by ID."""
        ...

    def search_rows(
        self,
        table: str,
        column: str,
        value: typing.Any,
        operator: str = "=",
    ) -> list[int]:
        """Return IDs of rows where ``column <operator> value``.

        Supports: ``=``, ``!=``, ``<``, ``<=``, ``>``, ``>=``,
        ``in``, ``not in``.
        """
        ...

    def next_id(self, table: str) -> int:
        """Return the next auto-incremented ID for *table* without inserting."""
        ...


class DictBackend:
    """In-memory storage backend for unit tests.

    Stores data as nested dicts: ``{table: {id: {column: value}}}``.
    Auto-increments IDs per table.

    Supports simple column-level searches via :meth:`search_rows` for
    relational field resolution (e.g. One2many reverse lookups).  Does
    NOT support SQL queries, domains, or joins.
    """

    __slots__ = ("_sequences", "_tables")

    def __init__(self) -> None:
        self._tables: dict[str, dict[int, dict[str, typing.Any]]] = {}
        self._sequences: dict[str, int] = defaultdict(int)

    def fetch_rows(self, table: str, ids: list[int], columns: list[str]) -> list[tuple]:
        tbl = self._tables.get(table, {})
        result = []
        for id_ in ids:
            row = tbl.get(id_)
            if row is not None:
                result.append(tuple(row.get(col) for col in columns))
        return result

    def insert_rows(
        self, table: str, columns: list[str], rows: list[tuple]
    ) -> list[int]:
        tbl = self._tables.setdefault(table, {})
        new_ids: list[int] = []
        for row in rows:
            self._sequences[table] += 1
            id_ = self._sequences[table]
            tbl[id_] = dict(zip(columns, row, strict=False))
            new_ids.append(id_)
        return new_ids

    def update_rows(
        self, table: str, updates: list[tuple[int, dict[str, typing.Any]]]
    ) -> None:
        tbl = self._tables.get(table)
        if tbl is None:
            return
        for id_, values in updates:
            row = tbl.get(id_)
            if row is not None:
                row.update(values)

    def delete_rows(self, table: str, ids: list[int]) -> None:
        tbl = self._tables.get(table)
        if tbl is None:
            return
        for id_ in ids:
            tbl.pop(id_, None)

    def get_row(self, table: str, id_: int) -> dict[str, typing.Any] | None:
        """Return the full row dict for a single ID, or None."""
        return self._tables.get(table, {}).get(id_)

    def table_ids(self, table: str) -> list[int]:
        """Return all IDs in a table, in insertion order."""
        return list(self._tables.get(table, {}).keys())

    def row_count(self, table: str) -> int:
        """Return the number of rows in a table."""
        return len(self._tables.get(table, {}))

    def search_rows(
        self,
        table: str,
        column: str,
        value: typing.Any,
        operator: str = "=",
    ) -> list[int]:
        """Return IDs where ``column <operator> value``.

        Used by InMemoryEnvironment for One2many resolution: given a
        Many2one field ``partner_id = 5`` on ``sale.order``, find all
        order IDs where ``partner_id = 5``.

        >>> backend = DictBackend()
        >>> ids = backend.insert_rows("order", ["partner_id"], [(1,), (2,), (1,)])
        >>> backend.search_rows("order", "partner_id", 1)
        [1, 3]
        """
        op_fn = _OPERATORS.get(operator)
        if op_fn is None:
            raise ValueError(f"Unsupported operator: {operator!r}")
        tbl = self._tables.get(table, {})
        return [id_ for id_, row in tbl.items() if op_fn(row.get(column), value)]

    def next_id(self, table: str) -> int:
        """Return the next auto-incremented ID for *table* without inserting.

        This is used by the ORM's ``_create()`` to generate record IDs
        before populating the row data.
        """
        self._sequences[table] += 1
        return self._sequences[table]

    def __repr__(self) -> str:
        n_tables = len(self._tables)
        n_rows = sum(len(t) for t in self._tables.values())
        return f"<DictBackend tables={n_tables} rows={n_rows}>"
