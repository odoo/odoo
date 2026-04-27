# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpProductionBackorder(models.TransientModel):
    _inherit = 'mrp.production.backorder'

    def action_backorder(self):
        res = super().action_backorder()
        if self.env.context.get('barcode_trigger', False):
            return True
        return res
