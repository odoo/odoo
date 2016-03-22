# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
