# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PayOnDelivery(models.TransientModel):
    _name = 'pay.on.delivery'
    _description = 'Pay on Delivery'

    order_id = fields.Many2one(comodel_name='sale.order', compute='_compute_order_id')
    amount_on_delivery = fields.Monetary(related='order_id.amount_on_delivery')
    currency_id = fields.Many2one(related='order_id.currency_id')

    @api.depends_context('order_ids_to_confirm', 'order_ids_confirmed')
    def _compute_order_id(self):
        order_ids_confirmed = set(self.env.context.get('order_ids_confirmed', {}))
        self.order_id = next(
            (
                id_
                for id_ in self.env.context.get('order_ids_to_confirm', [])
                if id_ not in order_ids_confirmed
            ),
            False,
        )

    def _open_wizard(self, order_ids_to_confirm=()):
        assert bool(order_ids_to_confirm) ^ bool(self)
        if order_ids_to_confirm:
            wizard = self.with_context(order_ids_to_confirm=order_ids_to_confirm)
        else:
            wizard = self.ensure_one()
        return wizard._get_records_action(target='new')

    def action_confirm_payment(self):
        """Walk through the queue of orders whose payment must be collected before resuming the
        validation of the pickings that opened the wizard."""
        self.ensure_one()

        order_ids_confirmed = {*self.env.context.get('order_ids_confirmed', []), self.order_id.id}
        confirmed_self = self.with_context(order_ids_confirmed=list(order_ids_confirmed))
        if confirmed_self.order_id:
            # While the orders are not all confirmed, keep popping the wizard.
            return confirmed_self._open_wizard()

        if picking_ids := self.env.context.get('button_validate_picking_ids'):
            # All the orders are now confirmed; resume the validation process.
            return confirmed_self.env['stock.picking'].browse(picking_ids).button_validate()

        return True
