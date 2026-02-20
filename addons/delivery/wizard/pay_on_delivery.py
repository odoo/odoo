# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PayOnDelivery(models.TransientModel):
    _name = 'pay.on.delivery'
    _description = "Pay on Delivery"
    _confirmed_orders_context_key = 'payment_confirmed_order_ids'

    order_ids = fields.Many2many(comodel_name='sale.order', required=True)
    next_order_id = fields.Many2one(comodel_name='sale.order', compute='_compute_next_order_id')
    amount_on_delivery = fields.Monetary(related='next_order_id.amount_on_delivery')
    currency_id = fields.Many2one(related='next_order_id.currency_id')

    @api.depends_context(_confirmed_orders_context_key)
    def _compute_next_order_id(self):
        orders_to_confirm = self.order_ids - self._get_confirmed_orders()
        for wizard in self:
            wizard.next_order_id = (wizard.order_ids & orders_to_confirm)[:1]

    def action_confirm_next_payment(self):
        """Display a confirmation wizard for each order payment until all are confirmed.

        Since each order requires individual payment confirmation, we sequentially
        display a wizard for each payment before confirming them all.
        """
        self.ensure_one()
        return self._with_confirmed_orders(self.next_order_id)._get_next_action()

    def _get_next_action(self):
        self.ensure_one()
        if self.next_order_id:
            # While the orders are not all confirmed, keep poping new confirmation wizard.
            return self._get_records_action(name=self.env._("Pay on Delivery"), target='new')
        return self._get_final_action()

    def _get_final_action(self):
        self.ensure_one()
        if self.order_ids._action_confirm_payment_on_delivery():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': self.env._("The payment was collected successfully!"),
                    'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
                },
            }
        return True

    @api.model
    def _get_confirmed_orders(self):
        return self.env['sale.order'].browse(
            self.env.context.get(self._confirmed_orders_context_key, [])
        )

    @api.model
    def _with_confirmed_orders(self, orders):
        return self.with_context(**{
            self._confirmed_orders_context_key: self._get_confirmed_orders().ids + orders.ids
        })
