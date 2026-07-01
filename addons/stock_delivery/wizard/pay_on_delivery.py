# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PayOnDelivery(models.TransientModel):
    _inherit = 'pay.on.delivery'

    def action_confirm_payment(self):
        # Override to change the final action when called during a picking validation flow.
        self.ensure_one()
        confirmed_order_ids = {self.order_id.id} | set(
            self.env.context.get('confirmed_order_ids', [])
        )
        confirmed_self = self.with_context(confirmed_order_ids=list(confirmed_order_ids))

        order_ids_to_confirm = set(self.env.context.get('order_ids_to_confirm', []))
        if remaining_order_ids := order_ids_to_confirm - confirmed_order_ids:
            # While the orders are not all confirmed, keep popping new confirmation wizard.
            return confirmed_self.create({
                'order_id': next(iter(remaining_order_ids))
            })._get_records_action(target='new')

        if validating_picking_ids := self.env.context.get('button_validate_picking_ids'):
            # All the orders are now confirmed, resume the validation process. The payments are
            # confirmed in `stock.picking._action_done()`.
            validating_pickings = confirmed_self.env['stock.picking'].browse(validating_picking_ids)
            return validating_pickings.button_validate()

        return super().action_confirm_payment()
