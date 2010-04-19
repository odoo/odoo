# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import osv

class olap_load_column(osv.osv_memory):
    _name = "olap.load.column"
    _description = "Olap Load Column"

    def get_table_data(self, cr, uid, ids, context={}):

        """
        This function load column
        @param cr: the current row, from the database cursor,
        @param uid: the current user\'s ID for security checks,
        @param ids: List of load column,
        @return: dictionary of database columns window on give id

        """
        data = context and context.get('active_id', False) or False
        ids_cols = self.pool.get('olap.database.columns').search(cr, uid, \
                             ([('table_id', '=', data)]), context={})
        model_data_ids = self.pool.get('ir.model.data').search(cr, uid, \
                            [('model', '=', 'ir.ui.view'), \
                            ('name', '=', 'view_olap_database_columns_form')], context={})
        resource_id = self.pool.get('ir.model.data').read(cr, uid, \
                                model_data_ids, fields=['res_id'])[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str,ids_cols))+"])]",
            'name': 'Database Columns',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'olap.database.columns',
            'views': [(False,'tree'),(resource_id,'form')],
            'type': 'ir.actions.act_window',
        }

olap_load_column()

# vim: ts=4 sts=4 sw=4 si et