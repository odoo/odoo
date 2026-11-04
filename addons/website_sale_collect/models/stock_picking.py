# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self, vals):
        """Subscribe the parent partner to receive emails for archived in-store pickup partners."""
        res = super().write(vals)
        if 'partner_id' in vals:
            for picking in self.filtered(lambda pck: pck.carrier_id.delivery_type == 'in_store'):
                if (
                    picking.partner_id
                    and not picking.partner_id.active
                    and picking.partner_id.parent_id
                ):
                    picking.message_subscribe([picking.partner_id.parent_id.id])
        return res
