# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.sql import make_identifier, SQL, IDENT_RE


def _sql_table(table: str | SQL | None) -> SQL | None:
    """ Wrap an optional table as an SQL object. """
    if isinstance(table, str):
        return SQL.identifier(table) if IDENT_RE.match(table) else SQL(f"({table})")
    return table


def _sql_from_table(alias: str, table: SQL | None) -> SQL:
    """ Return a FROM clause element from ``alias`` and ``table``. """
    if table is None:
        return SQL.identifier(alias)
    return SQL("%s AS %s", table, SQL.identifier(alias))


def _sql_from_join(kind: SQL, alias: str, table: SQL | None, condition: SQL) -> SQL:
    """ Return a FROM clause element for a JOIN. """
    return SQL("%s %s ON (%s)", kind, _sql_from_table(alias, table), condition)


_SQL_JOINS = {
    "JOIN": SQL("JOIN"),
    "LEFT JOIN": SQL("LEFT JOIN"),
}


def _generate_table_alias(src_table_alias, link):
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


class Query(object):
    """ Simple implementation of a query object, managing tables with aliases,
    join clauses (with aliases, condition and parameters), where clauses (with
    parameters), order, limit and offset.

    :param cr: database cursor (for lazy evaluation)
    :param alias: name or alias of the table
    :param table: a table expression (``str`` or ``SQL`` object), optional
    """

    def __init__(self, cr, alias: str, table: (str | SQL | None) = None):
        # database cursor
        self._cr = cr

        # tables {alias: table(SQL|None)}
        self._tables = {alias: _sql_table(table)}

        # joins {alias: (kind(SQL), table(SQL|None), condition(SQL))}
        self._joins = {}

        # holds the list of WHERE conditions (to be joined with 'AND')
        self._where_clauses = []

        # order, limit, offset
        self._order = None
        self.limit = None
        self.offset = None

        # memoized result
        self._ids = None

    def make_alias(self, alias: str, link: str) -> str:
        """ Return an alias based on ``alias`` and ``link``. """
        return _generate_table_alias(alias, link)

    def add_table(self, alias: str, table: (str | SQL | None) = None):
        """ Add a table with a given alias to the from clause. """
        assert alias not in self._tables and alias not in self._joins, f"Alias {alias!r} already in {self}"
        self._tables[alias] = _sql_table(table)
        self._ids = None

    def add_join(self, kind: str, alias: str, table: str | SQL | None, condition: SQL):
        """ Add a join clause with the given alias, table and condition. """
        sql_kind = _SQL_JOINS.get(kind.upper())
        assert sql_kind is not None, f"Invalid JOIN type {kind!r}"
        assert alias not in self._tables, f"Alias {alias!r} already used"
        table = _sql_table(table)

        if alias in self._joins:
            assert self._joins[alias] == (sql_kind, table, condition)
        else:
            self._joins[alias] = (sql_kind, table, condition)
            self._ids = None

    def add_where(self, where_clause: str | SQL, where_params=()):
        """ Add a condition to the where clause. """
        self._where_clauses.append(SQL(where_clause, *where_params))
        self._ids = None

    def join(self, lhs_alias: str, lhs_column: str, rhs_table: str, rhs_column: str, link: str):
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
        assert lhs_alias in self._tables or lhs_alias in self._joins, "Alias %r not in %s" % (lhs_alias, str(self))
        rhs_alias = self.make_alias(lhs_alias, link)
        condition = SQL("%s = %s", SQL.identifier(lhs_alias, lhs_column), SQL.identifier(rhs_alias, rhs_column))
        self.add_join('JOIN', rhs_alias, rhs_table, condition)
        return rhs_alias

    def left_join(self, lhs_alias: str, lhs_column: str, rhs_table: str, rhs_column: str, link: str):
        """ Add a LEFT JOIN to the current table (if necessary), and return the
        alias corresponding to ``rhs_table``.

        See the documentation of :meth:`join` for a better overview of the
        arguments and what they do.
        """
        assert lhs_alias in self._tables or lhs_alias in self._joins, "Alias %r not in %s" % (lhs_alias, str(self))
        rhs_alias = self.make_alias(lhs_alias, link)
        condition = SQL("%s = %s", SQL.identifier(lhs_alias, lhs_column), SQL.identifier(rhs_alias, rhs_column))
        self.add_join('LEFT JOIN', rhs_alias, rhs_table, condition)
        return rhs_alias

    @property
    def order(self) -> SQL | None:
        return self._order

    @order.setter
    def order(self, value: SQL | str | None):
        self._order = SQL(value) if value is not None else None

    @property
    def table(self) -> str:
        """ Return the query's main table, i.e., the first one in the FROM clause. """
        return next(iter(self._tables))

    @property
    def from_clause(self) -> SQL:
        """ Return the FROM clause of ``self``, without the FROM keyword. """
        tables = SQL(", ").join(
            _sql_from_table(alias, table)
            for alias, table in self._tables.items()
        )
        if not self._joins:
            return tables
        items = [tables]
        for alias, (kind, table, condition) in self._joins.items():
            items.append(_sql_from_join(kind, alias, table, condition))
        return SQL(" ").join(items)

    @property
    def where_clause(self) -> SQL:
        """ Return the WHERE condition of ``self``, without the WHERE keyword. """
        return SQL(" AND ").join(self._where_clauses)

    def is_empty(self):
        """ Return whether the query is known to return nothing. """
        return self._ids == ()

    def select(self, *args: str | SQL) -> SQL:
        """ Return the SELECT query as an ``SQL`` object. """
        sql_args = map(SQL, args) if args else [SQL.identifier(self.table, 'id')]
        return SQL(
            "%s%s%s%s%s%s",
            SQL("SELECT %s", SQL(", ").join(sql_args)),
            SQL(" FROM %s", self.from_clause),
            SQL(" WHERE %s", self.where_clause) if self._where_clauses else SQL(),
            SQL(" ORDER BY %s", self._order) if self._order else SQL(),
            SQL(" LIMIT %s", self.limit) if self.limit else SQL(),
            SQL(" OFFSET %s", self.offset) if self.offset else SQL(),
        )

    def subselect(self, *args: str | SQL) -> SQL:
        """ Similar to :meth:`.select`, but for sub-queries.
            This one avoids the ORDER BY clause when possible,
            and includes parentheses around the subquery.
        """
        if self._ids is not None and not args:
            # inject the known result instead of the subquery
            return SQL("%s", self._ids or (None,))

        if self.limit or self.offset:
            # in this case, the ORDER BY clause is necessary
            return SQL("(%s)", self.select(*args))

        sql_args = map(SQL, args) if args else [SQL.identifier(self.table, 'id')]
        return SQL(
            "(%s%s%s)",
            SQL("SELECT %s", SQL(", ").join(sql_args)),
            SQL(" FROM %s", self.from_clause),
            SQL(" WHERE %s", self.where_clause) if self._where_clauses else SQL(),
        )

    def get_sql(self):
        """ Returns (query_from, query_where, query_params). """
        from_string, from_params = self.from_clause
        where_string, where_params = self.where_clause
        return from_string, where_string, from_params + where_params

    def get_result_ids(self):
        """ Return the result of ``self.select()`` as a tuple of ids. The result
        is memoized for future use, which avoids making the same query twice.
        """
        if self._ids is None:
            self._cr.execute(self.select())
            self._ids = tuple(row[0] for row in self._cr.fetchall())
        return self._ids

    def set_result_ids(self, ids, ordered=True):
        """ Set up the query to return the lines given by ``ids``. The parameter
        ``ordered`` tells whether the query must be ordered to match exactly the
        sequence ``ids``.
        """
        assert not (self._joins or self._where_clauses or self.limit or self.offset), \
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
                self.table, 'id',
                SQL('(SELECT * FROM unnest(%s) WITH ORDINALITY)', list(ids)), 'unnest',
                'ids',
            )
            self.order = SQL.identifier(alias, 'ordinality')
        else:
            self.add_where(SQL("%s IN %s", SQL.identifier(self.table, 'id'), ids))
        self._ids = ids

    def __str__(self):
        sql = self.select()
        return f"<Query: {sql.code!r} with params: {sql.params!r}>"

    def __bool__(self):
        return bool(self.get_result_ids())

    def __len__(self):
        if self._ids is None:
            if self.limit or self.offset:
                # optimization: generate a SELECT FROM, and then count the rows
                sql = SQL("SELECT COUNT(*) FROM (%s) t", self.select(""))
            else:
                sql = self.select('COUNT(*)')
            self._cr.execute(sql)
            return self._cr.fetchone()[0]
        return len(self.get_result_ids())

    def __iter__(self):
        return iter(self.get_result_ids())
