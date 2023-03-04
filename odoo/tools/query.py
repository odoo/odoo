# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.tools.sql import make_identifier

IDENT_RE = re.compile(r'^[a-z_][a-z0-9_$]*$', re.I)


def _from_table(table, alias):
    """ Return a FROM clause element from ``table`` and ``alias``. """
    if alias == table:
        return f'"{alias}"'
    elif IDENT_RE.match(table):
        return f'"{table}" AS "{alias}"'
    else:
        return f'({table}) AS "{alias}"'


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
    :param table: if given, a table expression (identifier or query)
    """

    def __init__(self, cr, alias, table=None):
        # database cursor
        self._cr = cr

        # tables {alias: table}
        self._tables = {alias: table or alias}

        # joins {alias: (kind, table, condition, condition_params)}
        self._joins = {}

        # holds the list of WHERE clause elements (to be joined with 'AND'), and
        # the list of parameters
        self._where_clauses = []
        self._where_params = []

        # order, limit, offset
        self.order = None
        self.limit = None
        self.offset = None

        # memoized result
        self._ids = None

    def add_table(self, alias, table=None):
        """ Add a table with a given alias to the from clause. """
        assert alias not in self._tables and alias not in self._joins, "Alias %r already in %s" % (alias, str(self))
        self._tables[alias] = table or alias
        self._ids = None

    def add_where(self, where_clause, where_params=()):
        """ Add a condition to the where clause. """
        self._where_clauses.append(where_clause)
        self._where_params.extend(where_params)
        self._ids = None

    def join(self, lhs_alias, lhs_column, rhs_table, rhs_column, link, extra=None, extra_params=()):
        """
        Perform a join between a table already present in the current Query object and
        another table.

        :param str lhs_alias: alias of a table already defined in the current Query object.
        :param str lhs_column: column of `lhs_alias` to be used for the join's ON condition.
        :param str rhs_table: name of the table to join to `lhs_alias`.
        :param str rhs_column: column of `rhs_alias` to be used for the join's ON condition.
        :param str link: used to generate the alias for the joined table, this string should
            represent the relationship (the link) between both tables.
        :param str extra: an sql string of a predicate or series of predicates to append to the
            join's ON condition, `lhs_alias` and `rhs_alias` can be injected if the string uses
            the `lhs` and `rhs` variables with the `str.format` syntax. e.g.::

                query.join(..., extra="{lhs}.name != {rhs}.name OR ...", ...)

        :param tuple extra_params: a tuple of values to be interpolated into `extra`, this is
            done by psycopg2.

        Full example:

        >>> rhs_alias = query.join(
        ...     "res_users",
        ...     "partner_id",
        ...     "res_partner",
        ...     "id",
        ...     "partner_id",           # partner_id is the "link" from res_users to res_partner
        ...     "{lhs}.\"name\" != %s",
        ...     ("Mitchell Admin",),
        ... )
        >>> rhs_alias
        res_users_res_partner__partner_id

        From the example above, the resulting query would be something like::

            SELECT ...
            FROM "res_users" AS "res_users"
            JOIN "res_partner" AS "res_users_res_partner__partner_id"
                ON "res_users"."partner_id" = "res_users_res_partner__partner_id"."id"
                AND "res_users"."name" != 'Mitchell Admin'
            WHERE ...

        """
        return self._join('JOIN', lhs_alias, lhs_column, rhs_table, rhs_column, link, extra, extra_params)

    def left_join(self, lhs_alias, lhs_column, rhs_table, rhs_column, link, extra=None, extra_params=()):
        """ Add a LEFT JOIN to the current table (if necessary), and return the
        alias corresponding to ``rhs_table``.

        See the documentation of :meth:`join` for a better overview of the
        arguments and what they do.
        """
        return self._join('LEFT JOIN', lhs_alias, lhs_column, rhs_table, rhs_column, link, extra, extra_params)

    def _join(self, kind, lhs_alias, lhs_column, rhs_table, rhs_column, link, extra=None, extra_params=()):
        assert lhs_alias in self._tables or lhs_alias in self._joins, "Alias %r not in %s" % (lhs_alias, str(self))

        rhs_alias = _generate_table_alias(lhs_alias, link)
        assert rhs_alias not in self._tables, "Alias %r already in %s" % (rhs_alias, str(self))

        if rhs_alias not in self._joins:
            condition = f'"{lhs_alias}"."{lhs_column}" = "{rhs_alias}"."{rhs_column}"'
            if extra:
                condition = condition + " AND " + extra.format(lhs=lhs_alias, rhs=rhs_alias)
            condition_params = list(extra_params)
            if kind:
                self._joins[rhs_alias] = (kind, rhs_table, condition, condition_params)
            else:
                self._tables[rhs_alias] = rhs_table
                self.add_where(condition, condition_params)
            self._ids = None

        return rhs_alias

    def select(self, *args):
        """ Return the SELECT query as a pair ``(query_string, query_params)``. """
        from_clause, where_clause, params = self.get_sql()
        query_str = 'SELECT {} FROM {} WHERE {}{}{}{}'.format(
            ", ".join(args or [f'"{next(iter(self._tables))}"."id"']),
            from_clause,
            where_clause or "TRUE",
            (" ORDER BY %s" % self.order) if self.order else "",
            (" LIMIT %d" % self.limit) if self.limit else "",
            (" OFFSET %d" % self.offset) if self.offset else "",
        )
        return query_str, params

    def subselect(self, *args):
        """ Similar to :meth:`.select`, but for sub-queries.
            This one avoids the ORDER BY clause when possible,
            and includes parentheses around the subquery.
        """
        if self._ids is not None and not args:
            # inject the known result instead of the subquery
            return "%s", [self._ids or (None,)]

        if self.limit or self.offset:
            # in this case, the ORDER BY clause is necessary
            query_str, params = self.select(*args)
            return f"({query_str})", params

        from_clause, where_clause, params = self.get_sql()
        query_str = '(SELECT {} FROM {} WHERE {})'.format(
            ", ".join(args or [f'"{next(iter(self._tables))}"."id"']),
            from_clause,
            where_clause or "TRUE",
        )
        return query_str, params

    def is_empty(self):
        """ Return whether the query is known to return nothing. """
        return self._ids == ()

    def get_sql(self):
        """ Returns (query_from, query_where, query_params). """
        tables = [_from_table(table, alias) for alias, table in self._tables.items()]
        joins = []
        params = []
        for alias, (kind, table, condition, condition_params) in self._joins.items():
            joins.append(f'{kind} {_from_table(table, alias)} ON ({condition})')
            params.extend(condition_params)

        from_clause = " ".join([", ".join(tables)] + joins)
        where_clause = " AND ".join(self._where_clauses)
        return from_clause, where_clause, params + self._where_params

    def get_result_ids(self):
        """ Return the result of ``self.select()`` as a tuple of ids. The result
        is memoized for future use, which avoids making the same query twice.
        """
        if self._ids is None:
            query_str, params = self.select()
            self._cr.execute(query_str, params)
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
            #   WHERE TRUE
            #   ORDER BY "stuff__ids"."ordinality"
            alias = self.join(
                next(iter(self._tables)), 'id',
                'SELECT * FROM unnest(%s) WITH ORDINALITY', 'unnest',
                'ids', extra_params=[list(ids)],
            )
            self.order = f'"{alias}"."ordinality"'
        else:
            self.add_where(f'"{next(iter(self._tables))}"."id" IN %s', [ids])
        self._ids = ids

    def __str__(self):
        return '<osv.Query: %r with params: %r>' % self.select()

    def __bool__(self):
        return bool(self.get_result_ids())

    def __len__(self):
        if self._ids is None:
            if self.limit or self.offset:
                # optimization: generate a SELECT FROM, and then count the rows
                query_str, params = self.select('')
                query_str = f'SELECT COUNT(*) FROM ({query_str}) t'
            else:
                query_str, params = self.select('COUNT(*)')
            self._cr.execute(query_str, params)
            return self._cr.fetchone()[0]
        return len(self.get_result_ids())

    def __iter__(self):
        return iter(self.get_result_ids())

    #
    # deprecated attributes and methods
    #
    @property
    def where_clause(self):
        return tuple(self._where_clauses)

    @property
    def where_clause_params(self):
        return tuple(self._where_params)
