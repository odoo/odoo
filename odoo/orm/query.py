# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import LiteralString
    from .fields import Field
    from .models import BaseModel

from odoo.tools.sql import SQL, make_identifier


def _sql_from_table(alias: str, table: SQL) -> SQL:
    """ Return a FROM clause element from ``alias`` and ``table``. """
    if (alias_identifier := SQL.identifier(alias)) == table:
        return table
    return SQL("%s AS %s", table, alias_identifier)


_SQL_EMPTY = SQL()
_SQL_JOINS = {
    "JOIN": SQL("JOIN"),
    "LEFT JOIN": SQL("LEFT JOIN"),
    "LEFT JOIN LATERAL": SQL("LEFT JOIN LATERAL"),
}


def _generate_table_alias(src_table_alias: str, link: str) -> str:
    """ Generate a standard table alias name. An alias is generated as following:

        - the base is the source table name (that can already be an alias)
        - then, the joined table is added in the alias using a 'link field name'
          that is used to render unique aliases for a given path
        - the name is shortcut if it goes beyond PostgreSQL's identifier limits

        .. code-block:: pycon

            >>> _generate_table_alias('res_users', link='parent_id')
            'res_users__parent_id'

        :param str src_table_alias: alias of the source table
        :param str link: field name
        :return str: alias
    """
    return make_identifier(f"{src_table_alias}__{link}")


class Query:
    """ Simple implementation of a query object, managing tables with aliases,
    join clauses (with aliases, condition and parameters), where clauses (with
    parameters), group by, order, limit and offset.
    """

    def __init__(self, model: BaseModel | None, alias: (str | None) = None, table: (SQL | None) = None):
        # database cursor
        self._model = model

        if alias is None:
            alias = model._table
        if table is None:
            table = model._table_sql

        # joins {alias: (kind(SQL), table(SQL), condition(SQL))}
        self._joins: dict[str, tuple[SQL, SQL, SQL]] = {
            # first entry is the FROM table
            alias: (_SQL_EMPTY, table, _SQL_EMPTY),
        }

        # holds the list of WHERE conditions (to be joined with 'AND')
        self._where_clauses: list[SQL] = []

        # groupby, having, order, limit, offset
        self.groupby: SQL | None = None
        self._order_groupby: list[SQL] = []
        self.having: SQL | None = None
        self._order: SQL | None = None
        self.limit: int | None = None
        self.offset: int | None = None

        # memoized result
        self._ids: tuple[int, ...] | None = None

    @staticmethod
    def make_alias(alias: str, link: str) -> str:
        """ Return an alias based on ``alias`` and ``link``. """
        return _generate_table_alias(alias, link)

    def add_join(self, kind: str, alias: str | TableSQL, table: str | SQL | None, condition: SQL):
        """ Add a join clause with the given alias, table and condition. """
        sql_kind = _SQL_JOINS.get(kind.upper())
        assert sql_kind is not None, f"Invalid JOIN type {kind!r}"
        if isinstance(alias, TableSQL):
            if table is None and alias._model is not None:
                table = alias._model._table_sql
            alias = alias._alias
        elif table is None:
            table = alias
        if isinstance(table, str):
            table = SQL.identifier(table)

        if alias in self._joins:
            entry = self._joins[alias]
            if entry == (sql_kind, table, condition):
                return
            # this permits changing the kind to a non LEFT JOIN, as long as the
            # rest remains the same
            force_kind = kind != 'LEFT JOIN'
            if not (force_kind and entry[1:3] == (table, condition)):
                raise ValueError(f"Cannot change the JOIN condition from {entry!r}")

        self._joins[alias] = (sql_kind, table, condition)
        self._ids = self._ids and None

    def add_where(self, where_clause: LiteralString | SQL, where_params=()):
        """ Add a condition to the where clause. """
        self._where_clauses.append(SQL(where_clause, *where_params))  # pylint: disable = sql-injection
        self._ids = self._ids and None

    def join(self, lhs_alias: str, lhs_column: str, rhs_table: str | SQL, rhs_column: str, link: str) -> str:
        """
        Perform a join between a table already present in the current Query object and
        another table.  This method is essentially a shortcut for methods :meth:`~.make_alias`
        and :meth:`~.add_join`.

        :param str lhs_alias: alias of a table already defined in the current Query object.
        :param str lhs_column: column of `lhs_alias` to be used for the join's ON condition.
        :param str rhs_table: name of the table to join to `lhs_alias`.
        :param str rhs_column: column of `rhs_alias` to be used for the join's ON condition.
        :param str link: used to generate the alias for the joined table, this string should
            represent the relationship (the link) between both tables.
        """
        # TODO use TableSQL._join
        assert lhs_alias in self._joins, "Alias %r not in %s" % (lhs_alias, str(self))
        rhs_alias = self.make_alias(lhs_alias, link)
        condition = SQL("%s = %s", SQL.identifier(lhs_alias, lhs_column), SQL.identifier(rhs_alias, rhs_column))
        self.add_join('JOIN', rhs_alias, rhs_table, condition)
        return rhs_alias

    def left_join(self, lhs_alias: str, lhs_column: str, rhs_table: str, rhs_column: str, link: str) -> str:
        """ Add a LEFT JOIN to the current table (if necessary), and return the
        alias corresponding to ``rhs_table``.

        See the documentation of :meth:`join` for a better overview of the
        arguments and what they do.
        """
        # TODO use TableSQL._join
        assert lhs_alias in self._joins, "Alias %r not in %s" % (lhs_alias, str(self))
        rhs_alias = self.make_alias(lhs_alias, link)
        condition = SQL("%s = %s", SQL.identifier(lhs_alias, lhs_column), SQL.identifier(rhs_alias, rhs_column))
        self.add_join('LEFT JOIN', rhs_alias, rhs_table, condition)
        return rhs_alias

    @property
    def order(self) -> SQL | None:
        return self._order

    @order.setter
    def order(self, value: SQL | LiteralString | None):
        self._order = SQL(value) if value is not None else None  # pylint: disable = sql-injection

    @property
    def table(self) -> TableSQL:
        """ The query's main table, i.e., the first one in the FROM clause. """
        alias = next(iter(self._joins))
        return TableSQL(alias, self._model, self)

    @property
    def from_clause(self) -> SQL:
        """ Return the FROM clause of ``self``, without the FROM keyword. """
        return SQL(" ").join(
            SQL("%s %s ON (%s)", kind, _sql_from_table(alias, table), condition)
            if kind else _sql_from_table(alias, table)  # first table
            for alias, (kind, table, condition) in self._joins.items()
        )

    @property
    def where_clause(self) -> SQL:
        """ Return the WHERE condition of ``self``, without the WHERE keyword. """
        return SQL(" AND ").join(self._where_clauses)

    def is_empty(self) -> bool:
        """ Return whether the query is known to return nothing. """
        return self._ids == ()

    def select(self, *args: SQL | LiteralString) -> SQL:
        """ Return the SELECT query as an ``SQL`` object. """
        select_clause = SQL(", ").join(map(SQL, args)) if args else self.table.id
        return SQL(
            "%s%s%s%s%s%s%s%s",
            SQL("SELECT %s", select_clause),
            SQL(" FROM %s", self.from_clause),
            SQL(" WHERE %s", self.where_clause) if self._where_clauses else _SQL_EMPTY,
            SQL(" GROUP BY %s", self.groupby) if self.groupby else _SQL_EMPTY,
            SQL(" HAVING %s", self.having) if self.having else _SQL_EMPTY,
            SQL(" ORDER BY %s", self._order) if self._order else _SQL_EMPTY,
            SQL(f" LIMIT {int(self.limit)}") if self.limit is not None else _SQL_EMPTY,
            SQL(f" OFFSET {int(self.offset)}") if self.offset else _SQL_EMPTY,
        )

    def subselect(self, *args: SQL | LiteralString) -> SQL:
        """ Similar to :meth:`.select`, but for sub-queries.
            This one avoids the ORDER BY clause when possible,
            and includes parentheses around the subquery.
        """
        if self._ids is not None and not args:
            # inject the known result instead of the subquery
            if not self._ids:
                # in case we have nothing, we want to use a sub_query with no records
                # because an empty tuple leads to a syntax error
                # and a tuple containing just None creates issues for `NOT IN`
                return SQL("(SELECT 1 WHERE FALSE)")
            return SQL("%s", self._ids)

        if self.limit is not None or self.offset:
            # in this case, the ORDER BY clause is necessary
            return SQL("(%s)", self.select(*args))

        select_clause = SQL(", ").join(map(SQL, args)) if args else self.table.id
        return SQL(
            "(%s%s%s%s%s)",
            SQL("SELECT %s", select_clause),
            SQL(" FROM %s", self.from_clause),
            SQL(" WHERE %s", self.where_clause) if self._where_clauses else _SQL_EMPTY,
            SQL(" GROUP BY %s", self.groupby) if self.groupby else _SQL_EMPTY,
            SQL(" HAVING %s", self.having) if self.having else _SQL_EMPTY,
        )

    def get_result_ids(self) -> tuple[int, ...]:
        """ Return the result of ``self.select()`` as a tuple of ids. The result
        is memoized for future use, which avoids making the same query twice.
        """
        if self._ids is None:
            self._ids = tuple(id_ for id_, in self._model.env.execute_query(self.select()))
        return self._ids

    def set_result_ids(self, ids: Iterable[int], ordered: bool = True) -> None:
        """ Set up the query to return the lines given by ``ids``. The parameter
        ``ordered`` tells whether the query must be ordered to match exactly the
        sequence ``ids``.
        """
        assert not (len(self._joins) > 1 or self._where_clauses or self.limit or self.offset), \
            "Method set_result_ids() can only be called on a virgin Query"
        ids = tuple(ids)
        if not ids:
            self.add_where("FALSE")
        elif ordered:
            # This guarantees that self.select() returns the results in the
            # expected order of ids:
            #   SELECT "stuff".id
            #   FROM "stuff"
            #   JOIN (SELECT * FROM unnest(%s) WITH ORDINALITY) AS "stuff__ids"
            #       ON ("stuff"."id" = "stuff__ids"."unnest")
            #   ORDER BY "stuff__ids"."ordinality"
            alias = self.join(
                self.table._alias, 'id',
                SQL('(SELECT * FROM unnest(%s) WITH ORDINALITY)', list(ids)), 'unnest',
                'ids',
            )
            self.order = SQL.identifier(alias, 'ordinality')
        else:
            self.add_where(SQL("%s IN %s", self.table.id, ids))
        self._ids = ids

    def __str__(self) -> str:
        return f"<Query: {self.select()!r}>"

    def __bool__(self):
        return bool(self.get_result_ids())

    def __len__(self) -> int:
        if self._ids is None:
            if self.limit or self.offset:
                # optimization: generate a SELECT FROM, and then count the rows
                sql = SQL("SELECT COUNT(*) FROM (%s) t", self.select(""))
            else:
                sql = self.select('COUNT(*)')
            return self._model.env.execute_query(sql)[0][0]
        return len(self.get_result_ids())

    def __iter__(self) -> Iterator[int]:
        return iter(self.get_result_ids())


class TableSQL(SQL):
    """An alias of a table in a Query."""
    __slots__ = ('_alias', '_model', '_query')

    def __init__(self, alias: str, model: BaseModel | None, query: Query):
        assert isinstance(alias, str)
        self._alias = alias
        self._model = model
        self._query = query

    @property
    def _sql_tuple(self):
        return SQL.identifier(self._alias)._sql_tuple

    def __getitem__(self, field_name: str) -> SQL:
        if (model := self._model) is None:
            return SQL.identifier(self._alias, field_name)
        field = model._fields.get(field_name)
        if field is None:
            raise ValueError(f"Invalid field {field_name!r} on model {model._name!r}")
        return FieldSQL(self, field)

    __getattr__ = __getitem__

    def __repr__(self):
        return f"TableSQL({self._alias!r}, {self._model._name if self._model else '-'}, {self._query!r})"

    def _with_model(self, model: BaseModel) -> TableSQL:
        """ Bind a model to a new instance. """
        assert self._model is None or self._model._name == model._name
        return TableSQL(self._alias, model, self._query)

    def _sudo(self, flag: bool = True) -> TableSQL:
        """ Like `_with_model`, just sudo existing model. """
        if self._model is None or self._model.env.su == flag:
            return self
        return self._with_model(self._model.sudo(flag))

    def _make_alias(self, link: str, model: BaseModel | None = None) -> TableSQL:
        """ Generate a new table/alias using this as source. """
        return TableSQL(_generate_table_alias(self._alias, link), model, self._query)

    def _join(
        self,
        field_name: str,
        **kw,
    ) -> TableSQL:
        """ Join a table.

        Given a field, use its `Field.join` to join to another model.
        """
        model = self._model
        if model is None:
            raise ValueError(f"Cannot {self}._join() without a model")
        field = model._fields.get(field_name)
        if not field:
            raise ValueError(f"Invalid field {field_name!r} on model {model._name!r}")
        if hasattr(field, 'join') and callable(field.join):
            return field.join(self, **kw)
        raise ValueError(f"Invalid field {field_name}: _join() not possible")


class FieldSQL(SQL):
    """ An SQL object that represents the expression of a field.

    Accessing an attribute builds the SQL for the property of the field.
    """
    __slots__ = ('__sql_tuple', '_field', '_table')

    def __init__(self, table: TableSQL, field: Field):
        self._table = table
        self._field = field
        # Generate the SQL eagerly, it may be used multiple times and is easier
        # to debug than generating it lazily.
        self.__sql_tuple = field.to_sql(table)._sql_tuple

    @property
    def _sql_tuple(self):
        return self.__sql_tuple

    def __getitem__(self, name: str) -> SQL:
        return self._field.property_to_sql(self, name)

    __getattr__ = __getitem__

    def __repr__(self):
        return f"{self._table!r}.{self._field.name}"
