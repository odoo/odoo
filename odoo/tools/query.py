import itertools
from typing import TYPE_CHECKING

from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL, normalize_identifier

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from odoo.api import Environment

_debug = DebugLog(__name__)


def _prepare_table_sql(alias: str, table: SQL) -> SQL:
    if (alias_identifier := SQL.identifier(alias)) == table:
        return table
    return SQL("%s AS %s", table, alias_identifier)


def _prepare_join_sql(kind: SQL, alias: str, table: SQL, condition: SQL) -> SQL:
    return SQL("%s %s ON (%s)", kind, _prepare_table_sql(alias, table), condition)


_SQL_JOINS = {
    "JOIN": SQL("JOIN"),
    "LEFT JOIN": SQL("LEFT JOIN"),
}


def _generate_table_alias(src_table_alias: str, link: str) -> str:
    return normalize_identifier(f"{src_table_alias}__{link}")


class Query:
    __slots__ = (
        "_any_value_orderby",
        "_collect_order_groupby",
        "_empty_by_construction",
        "_env",
        "_groupby",
        "_having",
        "_ids",
        "_joins",
        "_limit",
        "_offset",
        "_order",
        "_order_groupby",
        "_tables",
        "_where_clauses",
    )

    def __init__(self, env: Environment, alias: str, table: SQL | None = None) -> None:
        self._env = env

        self._tables: dict[str, SQL] = {
            alias: table if table is not None else SQL.identifier(alias),
        }

        self._joins: dict[str, tuple[SQL, SQL, SQL]] = {}

        self._where_clauses: list[SQL] = []

        self._groupby: SQL | None = None
        self._order_groupby: list[SQL] = []
        self._any_value_orderby: bool = False
        self._collect_order_groupby: bool = False
        self._having: SQL | None = None
        self._order: SQL | None = None
        self._limit: int | None = None
        self._offset: int | None = None

        self._ids: tuple[int, ...] | None = None

        self._empty_by_construction: bool = False

    def _invalidate_ids(self) -> None:
        if self._ids:
            self._ids = None

    def _drop_ids(self) -> None:
        self._ids = None

    @staticmethod
    def get_table_alias(alias: str, link: str) -> str:
        return _generate_table_alias(alias, link)

    def add_table(self, alias: str, table: SQL | None = None) -> None:
        if alias in self._tables or alias in self._joins:
            raise ValueError(f"Alias {alias!r} already in {self}")
        self._tables[alias] = table if table is not None else SQL.identifier(alias)
        self._invalidate_ids()

    def add_join(
        self, kind: str, alias: str, table: str | SQL | None, condition: SQL
    ) -> None:
        sql_kind = _SQL_JOINS.get(kind.upper())
        if sql_kind is None:
            raise ValueError(f"Invalid JOIN type {kind!r}")
        if alias in self._tables:
            raise ValueError(f"Alias {alias!r} already used")
        table = table or alias
        if isinstance(table, str):
            table = SQL.identifier(table)

        if alias in self._joins:
            if self._joins[alias] != (sql_kind, table, condition):
                raise ValueError(f"Alias {alias!r} already used with a different join")
        else:
            self._joins[alias] = (sql_kind, table, condition)
            self._invalidate_ids()

    def copy(self) -> Query:
        """A query with this one's state, sharing none of its mutable parts.

        A `Query` handed to a domain -- `("line_ids", "in", query)` -- is still
        the caller's object, so a field that has to narrow it by its own
        `domain=` narrows this copy instead. Without it the caller's query is
        filtered for every later use of it.
        """
        other = Query.__new__(Query)
        for slot in Query.__slots__:
            value = getattr(self, slot)
            if type(value) is dict:
                value = dict(value)
            elif type(value) is list:
                value = list(value)
            setattr(other, slot, value)
        return other

    def add_where(self, where_clause: SQL) -> None:
        self._where_clauses.append(where_clause)
        self._invalidate_ids()

    def _join_on_column(
        self,
        kind: str,
        lhs_alias: str,
        lhs_column: str,
        rhs_table: str | SQL,
        rhs_column: str,
        link: str,
    ) -> str:
        assert lhs_alias in self._tables or lhs_alias in self._joins, (
            "Alias %r not in %s" % (lhs_alias, str(self))
        )
        rhs_alias = self.get_table_alias(lhs_alias, link)
        condition = SQL(
            "%s = %s",
            SQL.identifier(lhs_alias, lhs_column),
            SQL.identifier(rhs_alias, rhs_column),
        )
        self.add_join(kind, rhs_alias, rhs_table, condition)
        return rhs_alias

    def join(
        self,
        lhs_alias: str,
        lhs_column: str,
        rhs_table: str | SQL,
        rhs_column: str,
        link: str,
    ) -> str:
        return self._join_on_column(
            "JOIN", lhs_alias, lhs_column, rhs_table, rhs_column, link
        )

    def left_join(
        self,
        lhs_alias: str,
        lhs_column: str,
        rhs_table: str | SQL,
        rhs_column: str,
        link: str,
    ) -> str:
        return self._join_on_column(
            "LEFT JOIN", lhs_alias, lhs_column, rhs_table, rhs_column, link
        )

    @property
    def order(self) -> SQL | None:
        return self._order

    @order.setter
    def order(self, value: SQL | None) -> None:
        self._order = value
        self._invalidate_ids()

    @property
    def groupby(self) -> SQL | None:
        return self._groupby

    @groupby.setter
    def groupby(self, value: SQL | None) -> None:
        self._groupby = value
        self._invalidate_ids()

    @property
    def having(self) -> SQL | None:
        return self._having

    @having.setter
    def having(self, value: SQL | None) -> None:
        self._having = value
        self._invalidate_ids()

    @property
    def limit(self) -> int | None:
        return self._limit

    @limit.setter
    def limit(self, value: int | None) -> None:
        self._limit = value
        self._drop_ids()

    @property
    def offset(self) -> int | None:
        return self._offset

    @offset.setter
    def offset(self, value: int | None) -> None:
        self._offset = value
        self._drop_ids()

    @property
    def table(self) -> str:
        return next(iter(self._tables))

    @property
    def from_clause(self) -> SQL:
        tables = SQL(" CROSS JOIN ").join(
            itertools.starmap(_prepare_table_sql, self._tables.items())
        )
        if not self._joins:
            return tables
        items = (
            tables,
            *(
                _prepare_join_sql(kind, alias, table, condition)
                for alias, (kind, table, condition) in self._joins.items()
            ),
        )
        return SQL(" ").join(items)

    @property
    def where_clause(self) -> SQL:
        return SQL(" AND ").join(self._where_clauses)

    def is_empty(self) -> bool:
        return self._empty_by_construction or self._ids == ()

    def select(self, *args: str | SQL) -> SQL:
        sql_args = map(SQL, args) if args else [SQL.identifier(self.table, "id")]
        return SQL(
            "%s%s%s%s%s%s%s%s",
            SQL("SELECT %s", SQL(", ").join(sql_args)),
            SQL(" FROM %s", self.from_clause),
            (SQL(" WHERE %s", self.where_clause) if self._where_clauses else SQL.EMPTY),
            SQL(" GROUP BY %s", self.groupby) if self.groupby else SQL.EMPTY,
            SQL(" HAVING %s", self.having) if self.having else SQL.EMPTY,
            SQL(" ORDER BY %s", self._order) if self._order else SQL.EMPTY,
            SQL(" LIMIT %s", self.limit) if self.limit is not None else SQL.EMPTY,
            SQL(" OFFSET %s", self.offset) if self.offset else SQL.EMPTY,
        )

    def subselect(self, *args: str | SQL) -> SQL:
        if self.groupby or self.having:
            raise ValueError(
                "Query.subselect() does not support groupby/having; "
                "use select() or count_matching()"
            )

        if self._ids is not None and not args:
            if not self._ids:
                return SQL("(SELECT 1 WHERE FALSE)")
            return SQL("%s", self._ids)

        if self.limit is not None or self.offset:
            return SQL("(%s)", self.select(*args))

        sql_args = map(SQL, args) if args else [SQL.identifier(self.table, "id")]
        return SQL(
            "(%s%s%s)",
            SQL("SELECT %s", SQL(", ").join(sql_args)),
            SQL(" FROM %s", self.from_clause),
            (SQL(" WHERE %s", self.where_clause) if self._where_clauses else SQL.EMPTY),
        )

    def get_result_ids(self, env: Environment | None = None) -> tuple[int, ...]:
        """Ids of the rows matched by this query.

        :param env: environment to execute on, when the caller has a live one.
            A query may outlive the request that built it -- a record rule
            domain is cached across requests, and the queries inside it come
            along -- and by then its own environment holds a closed cursor.
        :return: the matched ids
        """
        if self._empty_by_construction:
            self._ids = ()
            return self._ids

        if env is None or env.cr is self._env.cr:
            if self._ids is None:
                self._ids = tuple(
                    id_ for (id_,) in self._env.execute_query(self.select())
                )
                _debug.perf.count(
                    "query.result_ids",
                    table=self.table,
                    joins=len(self._joins),
                    rows=len(self._ids),
                    limit=self.limit,
                )
            return self._ids

        # Another transaction: the result is neither read from nor written to
        # the memo, which belongs to the cursor that built this query and would
        # otherwise hand back rows read in a transaction that already ended.
        _debug.logic("query.result_ids.foreign_transaction", table=self.table)
        return tuple(id_ for (id_,) in env.execute_query(self.select()))

    def set_result_ids(self, ids: Iterable[int], ordered: bool = True) -> None:
        if self._joins or self._where_clauses or self.limit is not None or self.offset:
            raise ValueError(
                "Method set_result_ids() can only be called on a virgin Query"
            )
        ids = tuple(ids)
        _debug.logic(
            "query.result_ids_pinned", table=self.table, ids=len(ids), ordered=ordered
        )
        if not ids:
            self.add_where(SQL("FALSE"))
            self._empty_by_construction = True
        elif ordered:
            alias = self.join(
                self.table,
                "id",
                SQL("(SELECT * FROM unnest(%s) WITH ORDINALITY)", list(ids)),
                "unnest",
                "ids",
            )
            self.order = SQL.identifier(alias, "ordinality")
        else:
            self.add_where(
                SQL("%s = ANY(%s)", SQL.identifier(self.table, "id"), list(ids))
            )
        self._ids = ids

    def __str__(self) -> str:
        sql = self.select()
        return f"<Query: {sql.code!r} with params: {sql.params!r}>"

    def __bool__(self) -> bool:
        return bool(self.get_result_ids())

    def __len__(self) -> int:
        if self._ids is None:
            if self.limit is not None or self.offset or self.groupby or self.having:
                sql = SQL("SELECT COUNT(*) FROM (%s) t", self.select(""))
            else:
                sql = self.select("COUNT(*)")
            count = self._env.execute_query(sql)[0][0]
            _debug.perf.count(
                "query.len_counted",
                table=self.table,
                joins=len(self._joins),
                count=count,
                wrapped=self.limit is not None or bool(self.offset),
            )
            return count
        return len(self.get_result_ids())

    def count_matching(self, limit: int | None = None) -> int:
        if self._empty_by_construction:
            return 0
        if (
            self._ids is not None
            and self.limit is None
            and not self.offset
            and not self.groupby
            and not self.having
        ):
            return len(self._ids) if limit is None else min(len(self._ids), limit)

        _debug.perf.count(
            "query.count_matching",
            table=self.table,
            joins=len(self._joins),
            limit=limit,
            subquery=bool(self.groupby or self.having or limit is not None),
        )
        if self.groupby or self.having or limit is not None:
            parts = [SQL("SELECT FROM %s", self.from_clause)]
            if self._where_clauses:
                parts.append(SQL(" WHERE %s", self.where_clause))
            if self.groupby:
                parts.append(SQL(" GROUP BY %s", self.groupby))
            if self.having:
                parts.append(SQL(" HAVING %s", self.having))
            if limit is not None:
                parts.append(SQL(" LIMIT %s", limit))
            return self._env.execute_query(
                SQL("SELECT COUNT(*) FROM (%s) t", SQL("").join(parts))
            )[0][0]
        sql = SQL("SELECT COUNT(*) FROM %s", self.from_clause)
        if self._where_clauses:
            sql = SQL("%s WHERE %s", sql, self.where_clause)
        return self._env.execute_query(sql)[0][0]

    def __iter__(self) -> Iterator[int]:
        return iter(self.get_result_ids())
