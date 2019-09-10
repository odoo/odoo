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

#
# Order Point Method:
#    - Order if the virtual stock of today is bellow the min of the defined order point
#

import threading
from openerp.osv import fields,osv
from openerp.api import Environment

class procurement_compute(osv.osv_memory):
    _name = 'procurement.orderpoint.compute'
    _description = 'Compute Minimum Stock Rules'


    def _procure_calculation_orderpoint(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        with Environment.manage():
            proc_obj = self.pool.get('procurement.order')
            #As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            user_obj = self.pool.get('res.users')
            company_id = user_obj.browse(new_cr, uid, uid, context=context).company_id.id
            proc_obj._procure_orderpoint_confirm(new_cr, uid, use_new_cursor=new_cr.dbname, company_id = company_id, context=context)
            #close the new cursor
            new_cr.close()
            return {}

    def procure_calculation(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        
        threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint, args=(cr, uid, ids, context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
