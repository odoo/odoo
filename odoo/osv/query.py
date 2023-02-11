# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import warnings
from zlib import crc32

from odoo.tools import lazy_property

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

        Examples:
        - src_table_alias='res_users', link='parent_id'
            alias = 'res_users__parent_id'

        :param str src_table_alias: alias of the source table
        :param str link: field name
        :return str: alias
    """
    alias = "%s__%s" % (src_table_alias, link)
    # Use an alternate alias scheme if length exceeds the PostgreSQL limit
    # of 63 characters.
    if len(alias) >= 64:
        # We have to fit a crc32 hash and one underscore into a 63 character
        # alias. The remaining space we can use to add a human readable prefix.
        alias = "%s_%08x" % (alias[:54], crc32(alias.encode('utf-8')))
    return alias


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

    def add_table(self, alias, table=None):
        """ Add a table with a given alias to the from clause. """
        assert alias not in self._tables and alias not in self._joins, "Alias %r already in %s" % (alias, str(self))
        self._tables[alias] = table or alias

    def add_where(self, where_clause, where_params=()):
        """ Add a condition to the where clause. """
        self._where_clauses.append(where_clause)
        self._where_params.extend(where_params)

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

        See the documentation of :meth:`~odoo.osv.query.Query.join` for a better overview of the
        arguments and what they do.
        """
        return self._join('LEFT JOIN', lhs_alias, lhs_column, rhs_table, rhs_column, link, extra, extra_params)

    def _join(self, kind, lhs_alias, lhs_column, rhs_table, rhs_column, link, extra=None, extra_params=()):
        assert lhs_alias in self._tables or lhs_alias in self._joins, "Alias %r not in %s" % (lhs_alias, str(self))

        rhs_alias = _generate_table_alias(lhs_alias, link)
        assert rhs_alias not in self._tables, "Alias %r already in %s" % (rhs_alias, str(self))

        if rhs_alias not in self._joins:
            condition = f'"{lhs_alias}"."{lhs_column}" = "{rhs_alias}"."{rhs_column}"'
            condition_params = []
            if extra:
                condition = condition + " AND " + extra.format(lhs=lhs_alias, rhs=rhs_alias)
                condition_params = list(extra_params)
            if kind:
                self._joins[rhs_alias] = (kind, rhs_table, condition, condition_params)
            else:
                self._tables[rhs_alias] = rhs_table
                self.add_where(condition, condition_params)

        return rhs_alias

    def select(self, *args):
        """ Return the SELECT query as a pair ``(query_string, query_params)``. """
        from_clause, where_clause, params = self.get_sql()
        query_str = 'SELECT {} FROM {} WHERE {}{}{}{}'.format(
            ", ".join(args or [f'"{next(iter(self._tables))}".id']),
            from_clause,
            where_clause or "TRUE",
            (" ORDER BY %s" % self.order) if self.order else "",
            (" LIMIT %d" % self.limit) if self.limit else "",
            (" OFFSET %d" % self.offset) if self.offset else "",
        )
        return query_str, params

    def subselect(self, *args):
        """ Similar to :meth:`.select`, but for sub-queries.
            This one avoids the ORDER BY clause when possible.
        """
        if self.limit or self.offset:
            # in this case, the ORDER BY clause is necessary
            return self.select(*args)

        from_clause, where_clause, params = self.get_sql()
        query_str = 'SELECT {} FROM {} WHERE {}'.format(
            ", ".join(args or [f'"{next(iter(self._tables))}".id']),
            from_clause,
            where_clause or "TRUE",
        )
        return query_str, params

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

    @lazy_property
    def _result(self):
        query_str, params = self.select()
        self._cr.execute(query_str, params)
        return [row[0] for row in self._cr.fetchall()]

    def __str__(self):
        return '<osv.Query: %r with params: %r>' % self.select()

    def __bool__(self):
        return bool(self._result)

    def __len__(self):
        return len(self._result)

    def __iter__(self):
        return iter(self._result)

    #
    # deprecated attributes and methods
    #
    @property
    def tables(self):
        warnings.warn("deprecated Query.tables, use Query.get_sql() instead",
                      DeprecationWarning)
        return tuple(_from_table(table, alias) for alias, table in self._tables.items())

    @property
    def where_clause(self):
        return tuple(self._where_clauses)

    @property
    def where_clause_params(self):
        return tuple(self._where_params)

    def add_join(self, connection, implicit=True, outer=False, extra=None, extra_params=()):
        warnings.warn("deprecated Query.add_join, use Query.join() or Query.left_join() instead",
                      DeprecationWarning)
        lhs_alias, rhs_table, lhs_column, rhs_column, link = connection
        kind = '' if implicit else ('LEFT JOIN' if outer else 'JOIN')
        rhs_alias = self._join(kind, lhs_alias, lhs_column, rhs_table, rhs_column, link, extra, extra_params)
        return rhs_alias, _from_table(rhs_table, rhs_alias)
