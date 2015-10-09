# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Order Point Method:
#    - Order if the virtual stock of today is bellow the min of the defined order point
#

import threading
from openerp import api, models
from openerp.api import Environment

class ProcurementCompute(models.TransientModel):
    _name = 'procurement.orderpoint.compute'
    _description = 'Compute Minimum Stock Rules'

    @api.multi
    def _procure_calculation_orderpoint(self):
        """
        @param self: The object pointer.
        """
        with Environment.manage():
            #As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            self._cr = self.env.cursor()
            user_obj = self.pool.get('res.users')
            company_id = user_obj.browse(self._uid).company_id.id
            self.env['procurement.order']._procure_orderpoint_confirm(use_new_cursor=self._cr.dbname, company_id=company_id)
            #close the new cursor
            self._cr.close()
            return {}

    @api.multi
    def procure_calculation(self):
        """
        @param self: The object pointer.
        """
        threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint, args=(self._cr, self._uid, self.ids, self._context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
