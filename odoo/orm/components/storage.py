from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


@dataclass(slots=True)
class NamedSequence:
    increment: int
    last_value: int
    is_called: bool = False

    def next_values(self, count: int) -> list[int]:
        values = []
        for _ in range(count):
            if self.is_called:
                self.last_value += self.increment
            self.is_called = True
            values.append(self.last_value)
        return values

    def peek(self) -> int:
        return self.last_value + self.increment if self.is_called else self.last_value


class DictBackend:
    __slots__ = ("_named_sequences", "_sequences", "_tables")

    def __init__(self) -> None:
        self._tables: dict[str, dict[int, dict[str, Any]]] = {}
        self._sequences: dict[str, int] = defaultdict(int)
        self._named_sequences: dict[str, NamedSequence] = {}

    def snapshot(self) -> tuple:
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "storage.snapshot",
                tables=len(self._tables),
                rows=sum(len(rows) for rows in self._tables.values()),
                sequences=len(self._named_sequences),
            )
        # the sequences are deliberately absent: `nextval` is not
        # transactional on PostgreSQL, so a value a rolled-back savepoint
        # drew is spent and the next row takes the one after it
        return (
            {
                table: {id_: dict(row) for id_, row in rows.items()}
                for table, rows in self._tables.items()
            },
        )

    def restore(self, snapshot: tuple) -> None:
        (tables,) = snapshot
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "storage.restore",
                tables=len(tables),
                rows=sum(len(rows) for rows in tables.values()),
                sequences=len(self._named_sequences),
            )
        self._tables = {
            table: {id_: dict(row) for id_, row in rows.items()}
            for table, rows in tables.items()
        }

    def get_row_tuples(
        self, table: str, ids: list[int], columns: list[str]
    ) -> list[tuple]:
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
            tbl[id_] = dict(zip(columns, row, strict=True))
            new_ids.append(id_)
        return new_ids

    def put_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
        tbl = self._tables.setdefault(table, {})
        seq = self._sequences[table]
        for row in rows:
            id_ = row["id"]
            tbl[id_] = dict(row)
            seq = max(seq, id_)
        self._sequences[table] = seq

    def update_rows(
        self, table: str, updates: list[tuple[int, dict[str, Any]]]
    ) -> None:
        tbl = self._tables.get(table)
        if tbl is None:
            return
        for id_, values in updates:
            row = tbl.get(id_)
            if row is not None:
                row.update(values)

    def upsert_rows(
        self, table: str, updates: list[tuple[int, dict[str, Any]]]
    ) -> None:
        tbl = self._tables.setdefault(table, {})
        for id_, values in updates:
            row = tbl.get(id_)
            if row is not None:
                row.update(values)
            else:
                tbl[id_] = {"id": id_, **values}
                self._sequences[table] = max(self._sequences[table], id_)

    def remove_rows(self, table: str, ids: list[int]) -> None:
        tbl = self._tables.get(table)
        if tbl is None:
            return
        for id_ in ids:
            tbl.pop(id_, None)

    def get_row(self, table: str, id_: int) -> dict[str, Any] | None:
        row = self._tables.get(table, {}).get(id_)
        return dict(row) if row is not None else None

    def get_rows(self, table: str, ids: list[int]) -> dict[int, dict[str, Any]]:
        tbl = self._tables.get(table, {})
        result: dict[int, dict[str, Any]] = {}
        for id_ in ids:
            row = tbl.get(id_)
            if row is not None:
                result[id_] = dict(row)
        return result

    def get_existing_ids(self, table: str, ids: list[int]) -> set[int]:
        tbl = self._tables.get(table, {})
        return {id_ for id_ in ids if id_ in tbl}

    def get_table_ids(self, table: str) -> list[int]:
        return list(self._tables.get(table, {}).keys())

    def get_row_count(self, table: str) -> int:
        return len(self._tables.get(table, {}))

    def allocate_next_id(self, table: str) -> int:
        self._sequences[table] += 1
        return self._sequences[table]

    def __repr__(self) -> str:
        n_tables = len(self._tables)
        n_rows = sum(len(t) for t in self._tables.values())
        return f"<DictBackend tables={n_tables} rows={n_rows}>"
