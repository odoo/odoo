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

from openerp.osv import osv
from openerp.tools.translate import _


class pos_sales_user_today_current_user(osv.osv_memory):
    _name = 'pos.sales.user.today.current_user'
    _description = 'Sales Details'

    _columns = {
    }

    def print_report(self, cr, uid, ids, context=None):
        """
         To get the date and print the report
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return : retrun report
        """
        if context is None:
            context = {}

        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, [], context=context)
        res = res and res[0] or {}
        datas['form'] = res

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.sales.user.today.current.user',
            'datas': datas,
       }

pos_sales_user_today_current_user()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

