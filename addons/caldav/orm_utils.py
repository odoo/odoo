# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP SA (www.openerp.com)
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


if True: # we need this indentation level ;)

    def get_last_modified(self, cr, user, args, context=None, access_rights_uid=None):
        """Return the last modification date of objects in 'domain'
        This function has similar semantics to orm.search(), apart from the
        limit, offset and order arguments, which make no sense here.
        It is useful when we want to find if the table (aka set of records)
        has any modifications we should update at the client.
        """
        if context is None:
            context = {}
        self.pool.get('ir.model.access').check(cr, access_rights_uid or user, self._name, 'read', True)

        query = self._where_calc(cr, user, args, context=context)
        self._apply_ir_rules(cr, user, query, 'read', context=context)
        from_clause, where_clause, where_clause_params = query.get_sql()

        where_str = where_clause and (" WHERE %s" % where_clause) or ''

        cr.execute('SELECT MAX(COALESCE("%s".write_date, "%s".create_date)) FROM ' % (self._table, self._table) + 
                    from_clause + where_str ,
                    where_clause_params)
        res = cr.fetchall()
        return res[0][0]

#eof
