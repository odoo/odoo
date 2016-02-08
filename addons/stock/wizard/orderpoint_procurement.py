# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Order Point Method:
#    - Order if the virtual stock of today is bellow the min of the defined order point
#

import threading
from odoo import api, models
from odoo.api import Environment


class ProcurementCompute(models.TransientModel):
    _name = 'procurement.orderpoint.compute'
    _description = 'Compute Minimum Stock Rules'

    @api.multi
    def _procure_calculation_orderpoint(self):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        with Environment.manage():
            #  As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            self.env['procurement.order']._procure_orderpoint_confirm(use_new_cursor=new_cr.dbname, company_id=self.env.user.company_id.id, context=self.env.context)
            #  close the new cursor
            new_cr.close()
            return {}

    @api.multi
    def procure_calculation(self):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint())
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
