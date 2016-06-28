# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Order Point Method:
#    - Order if the virtual stock of today is bellow the min of the defined order point
#

from odoo import api, models

import threading


class ProcurementOrderpointConfirm(models.TransientModel):
    _name = 'procurement.orderpoint.compute'
    _description = 'Compute Minimum Stock Rules'

    def _procure_calculation_orderpoint(self):
        with api.Environment.manage():
            # As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            self.env['procurement.order']._procure_orderpoint_confirm(
                use_new_cursor=new_cr.dbname,
                company_id=self.env.user.company_id.id)
            new_cr.close()
            return {}

    @api.multi
    def procure_calculation(self):
        threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint, args=())
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
