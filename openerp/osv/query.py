# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP S.A. http://www.openerp.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#.apidoc title: Query object

def _quote(to_quote):
    if '"' not in to_quote:
        return '"%s"' % to_quote
    return to_quote


class Query(object):
    """
     Dumb implementation of a Query object, using 3 string lists so far
     for backwards compatibility with the (table, where_clause, where_params) previously used.

     TODO: To be improved after v6.0 to rewrite part of the ORM and add support for:
      - auto-generated multiple table aliases
      - multiple joins to the same table with different conditions
      - dynamic right-hand-side values in domains  (e.g. a.name = a.description)
      - etc.
    """

    def __init__(self, tables=None, where_clause=None, where_clause_params=None, joins=None):

        # holds the list of tables joined using default JOIN.
        # the table names are stored double-quoted (backwards compatibility)
        self.tables = tables or []

        # holds the list of WHERE clause elements, to be joined with
        # 'AND' when generating the final query
        self.where_clause = where_clause or []

        # holds the parameters for the formatting of `where_clause`, to be
        # passed to psycopg's execute method.
        self.where_clause_params = where_clause_params or []

        # holds table joins done explicitly, supporting outer joins. The JOIN
        # condition should not be in `where_clause`. The dict is used as follows:
        #   self.joins = {
        #                    'table_a': [
        #                                  ('table_b', 'table_a_col1', 'table_b_col', 'LEFT JOIN'),
        #                                  ('table_c', 'table_a_col2', 'table_c_col', 'LEFT JOIN'),
        #                                  ('table_d', 'table_a_col3', 'table_d_col', 'JOIN'),
        #                               ]
        #                 }
        #   which should lead to the following SQL:
        #       SELECT ... FROM "table_a" LEFT JOIN "table_b" ON ("table_a"."table_a_col1" = "table_b"."table_b_col")
        #                                 LEFT JOIN "table_c" ON ("table_a"."table_a_col2" = "table_c"."table_c_col")
        self.joins = joins or {}

    def join(self, connection, outer=False):
        """Adds the JOIN specified in ``connection``.

        :param connection: a tuple ``(lhs, table, lhs_col, col)``.
                           The join corresponds to the SQL equivalent of::

                                ``(lhs.lhs_col = table.col)``

        :param outer: True if a LEFT OUTER JOIN should be used, if possible
                      (no promotion to OUTER JOIN is supported in case the JOIN
                       was already present in the query, as for the moment
                       implicit INNER JOINs are only connected from NON-NULL
                       columns so it would not be correct (e.g. for
                       ``_inherits`` or when a domain criterion explicitly
                       adds filtering)
        """
        (lhs, table, lhs_col, col) = connection
        lhs = _quote(lhs)
        table = _quote(table)
        assert lhs in self.tables, "Left-hand-side table must already be part of the query!"
        if table in self.tables:
            # already joined, must ignore (promotion to outer and multiple joins not supported yet)
            pass
        else:
            # add JOIN
            self.tables.append(table)
            self.joins.setdefault(lhs, []).append((table, lhs_col, col, outer and 'LEFT JOIN' or 'JOIN'))
        return self

    def get_sql(self):
        """Returns (query_from, query_where, query_params)"""
        query_from = ''
        tables_to_process = list(self.tables)

        def add_joins_for_table(table, query_from):
            for (dest_table, lhs_col, col, join) in self.joins.get(table,[]):
                tables_to_process.remove(dest_table)
                query_from += ' %s %s ON (%s."%s" = %s."%s")' % \
                    (join, dest_table, table, lhs_col, dest_table, col)
                query_from = add_joins_for_table(dest_table, query_from)
            return query_from

        for table in tables_to_process:
            query_from += table
            if table in self.joins:
                query_from = add_joins_for_table(table, query_from)
            query_from += ','
        query_from = query_from[:-1] # drop last comma
        return (query_from, " AND ".join(self.where_clause), self.where_clause_params)

    def __str__(self):
        return '<osv.Query: "SELECT ... FROM %s WHERE %s" with params: %r>' % self.get_sql()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: