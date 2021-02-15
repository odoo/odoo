# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import warnings
import logging
from zlib import crc32

from odoo.tools import lazy_property

IDENT_RE = re.compile(r'^[a-z_][a-z0-9_$]*$', re.I)
_logger = logging.getLogger(__name__)


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

        # QueryUnion
        self._column_ref_replacement = {}

    def copy(self):
        query = Query(self._cr, next(iter(self._tables)))
        query._joins = self._joins.copy()
        query._where_clauses = self._where_clauses[:]
        query._where_params = self._where_params[:]
        query.order = self.order
        query.limit = self.limit
        query.offset = self.offset
        query._column_ref_replacement = self._column_ref_replacement.copy()
        return query

    def add_column_ref_replacement(self, source, target):
        self._column_ref_replacement[source] = target

    def add_table(self, alias, table=None):
        """ Add a table with a given alias to the from clause. """
        assert alias not in self._tables and alias not in self._joins, "Alias %r already in %s" % (alias, str(self))
        self._tables[alias] = table or alias

    def add_where(self, where_clause, where_params=()):
        """ Add a condition to the where clause. """
        self._where_clauses.append(where_clause)
        self._where_params.extend(where_params)

    def join(self, lhs_alias, lhs_column, rhs_table, rhs_column, link, extra=None, extra_params=()):
        """ Add an INNER JOIN to the current table (if necessary), and return
        the alias corresponding to ``rhs_table``.
        """
        return self._join('JOIN', lhs_alias, lhs_column, rhs_table, rhs_column, link, extra, extra_params)

    def left_join(self, lhs_alias, lhs_column, rhs_table, rhs_column, link, extra=None, extra_params=()):
        """ Add a LEFT JOIN to the current table (if necessary), and return the
        alias corresponding to ``rhs_table``.
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
        for source, target in self._column_ref_replacement.items():
            query_str = query_str.replace(source, target)
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


class QueryUnion(object):
    MAX_UNIONS = 2

    def __init__(self, queries):
        self._queries = queries

        # order, limit, offset
        self.order = None
        self.limit = None
        self.offset = None

    def left_join(self, *args, **kwargs):
        return self._apply_to_all('left_join', args, kwargs)

    def add_where(self, *args, **kwargs):
        return self._apply_to_all('add_where', args, kwargs)

    def add_column_ref_replacement(self, *args, **kwargs):
        return self._apply_to_all('add_column_ref_replacement', args, kwargs)

    def _apply_to_all(self, method, args, kwargs):
        res = set(getattr(q, method)(*args, **kwargs) for q in self._queries)
        # if all values are the same, return it
        if len(res) == 1:
            return res.pop()

    # TODO: get_sql may work with multiple quieries if we pass select args in advance
    def get_sql(self, *args, **kwargs):
        return self._one_query_only('get_sql', args, kwargs)

    def _one_query_only(self, method, args, kwargs):
        #if len(self._queries) > 1:
        #    import wdb; wdb.set_trace()
        assert len(self._queries) == 1, "QueryUnion has multiple queries, but is used as a single query"
        return getattr(self._queries[0], method)(*args, **kwargs)

    def fork(self):
        if len(self._queries) >= self.MAX_UNIONS:
            return self, None

        fork1 = self._queries[:]
        fork2 = [q.copy() for q in self._queries]
        self._queries += fork2
        return QueryUnion(fork1), QueryUnion(fork2)

    def select(self, *args):
        """ Return the SELECT query as a pair ``(query_string, query_params)``. """
        if len(self._queries) == 1:
            self._queries[0].order = self.order
            self._queries[0].limit = self.limit
            self._queries[0].offset = self.offset
            return self._queries[0].select(*args)
        if args:
            args = list(args)

        #from odoo.http import request
        #_logger.warning("QueryUnion select: %s", [self._queries[0]._tables, args, request.httprequest.url])
        all_query_str = []
        all_params = []
        priority = 0

        order = self.order or self._queries[0].order
        # TODO: choose a better names
        order_fields_to_select_local = []
        order_fields_to_select_global = []
        order_fields_to_order_global = []
        if order:
            # use regexp to exclude COALESCE in order by, e.g.
            # COALESCE("ir_module_module"."application", false) DESC,"ir_module_module"."sequence" ,"ir_module_module"."name"
            # https://stackoverflow.com/a/38748250 -- thanks for regexp
            for order_part in re.sub(r",(?![^\(\[]*[\]\)])", "\n", order).split("\n"):
                order_split = re.sub(r" (?![^\(\[]*[\]\)])", "\n", order_part.strip()).split("\n")
                order_field = order_split[0].strip()
                order_direction = order_split[1].strip().upper() if len(order_split) == 2 else ''
                field_global = order_field.replace('.', '_').replace('"', '_').replace('(', '_').replace(')', '_').replace(' ', '_').replace(',', '_')
                order_fields_to_select_local.append("%s AS %s" % (order_field, field_global))
                order_fields_to_select_global.append(field_global)
                order_fields_to_order_global.append("%s %s" % (field_global, order_direction))

        for query in self._queries:
            # TODO: 'count(1)' is too hardcoded
            select_local = args[:] if args and args != ['count(1)'] else [f'"{next(iter(query._tables))}".id']
            select_local += order_fields_to_select_local
            select_local.append("%s AS union_priority" % priority)
            # TODO: shall we pass order to query?
            query_str, params = query.select(*select_local)
            all_query_str.append(query_str)
            all_params.extend(params)
            priority += 1

        select_clause = ", ".join((args if args and args != ['count(1)'] else ['id']) + order_fields_to_select_global)
        main_query = " UNION ALL ".join("(%s)" % q for q in all_query_str)
        # TODO: do we always have id field ?
        main_query = "SELECT DISTINCT ON(id) {} FROM ({}) AS x ORDER BY id, union_priority".format(
            select_clause,
            main_query
        )
        order = ", ".join(order_fields_to_order_global)
        limit = self.limit or self._queries[0].limit
        offset = self.offset or self._queries[0].offset
        # TODO: combine this select with previous SELECT DISTINCT ?
        select_clause = ", ".join((args if args else ['id']) + order_fields_to_select_global)
        main_query = "SELECT {} FROM ({}) AS xx {}{}{}".format(
            select_clause,
            main_query,
            (" ORDER BY %s" % order) if order else "",
            (" LIMIT %d" % limit) if limit else "",
            (" OFFSET %d" % offset) if offset else "",
        )
        return main_query, all_params

    @lazy_property
    def _result(self):
        query_str, params = self.select()
        cr = self._queries[0]._cr
        cr.execute(query_str, params)
        return [row[0] for row in cr.fetchall()]

    def __str__(self):
        return '<osv.Query: %r with params: %r>' % self.select()

    def __bool__(self):
        return bool(self._result)

    def __len__(self):
        return len(self._result)

    def __iter__(self):
        return iter(self._result)
