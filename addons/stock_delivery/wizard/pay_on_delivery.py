# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PayOnDelivery(models.TransientModel):
    _inherit = 'pay.on.delivery'

    def _get_final_action(self):
        # Override to change the final action when called during a picking validation flow.
        self.ensure_one()
        if validating_picking_ids := self.env.context.get('button_validate_picking_ids'):
            # All the orders are now confirmed, resume the validation process. The payments are
            # confirmed in `stock.picking._action_done()`.
            validating_pickings = self.env['stock.picking'].browse(validating_picking_ids)
            return validating_pickings.button_validate()
        return super()._get_final_action()
