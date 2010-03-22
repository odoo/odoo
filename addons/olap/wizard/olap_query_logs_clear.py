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

from osv import fields, osv

class olap_query_logs_clear(osv.osv_memory):
    _name = "olap.query.logs.clear"
    _description = "Olap Query Logs Clear"

    _columns = {
        'user_name':fields.char('User', size=64, required=True, readonly=True), 
    }

    def _getdata(self, cr, uid, context={}):
        user = self.pool.get('res.users').browse(cr, uid, uid)
        return user.name

    _defaults = {
        'user_name': _getdata
            }

    def clear_logs(self, cr, uid, part, context={}):
        """
        This function load column
        @param cr: the current row, from the database cursor,
        @param uid: the current users ID for security checks,
        @param ids: List of load column,
        @return: dictionary of query logs clear message window
        """
        ids = self.pool.get('olap.query.logs').search(cr, uid, [('user_id', '=', uid)])
        self.pool.get('olap.query.logs').unlink(cr, uid, ids, context)
        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'olap', 'view_olap_query_logs_clear_msg')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        value = {
            'view_type': 'form', 
            'view_mode': 'form', 
            'res_model': 'olap.query.logs.clear.msg', 
            'views': [(id2, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')], 
            'type': 'ir.actions.act_window', 
            'target': 'new'
        }
        return value

olap_query_logs_clear()


class olap_query_logs_clear_msg(osv.osv_memory):
    """   Display clear log message    """
    _name = "olap.query.logs.clear.msg"
    _description = "Olap Query Logs Clear Message"

olap_query_logs_clear_msg()

# vim: ts=4 sts=4 sw=4 si et
