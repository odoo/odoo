# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class PayOnDelivery(models.TransientModel):
    _name = 'pay.on.delivery'
    _description = "Pay on Delivery"

    order_ids = fields.Many2many(comodel_name='sale.order', compute='_compute_order_ids')
    amount_to_collect = fields.Monetary(compute='_compute_amount_to_collect')
    currency_id = fields.Many2one(related='order_ids.currency_id')

    @api.depends_context('button_validate_picking_ids')
    def _compute_order_ids(self):
        self.order_ids = (
            self._get_pickings_to_validate()._filtered_pending_payment_on_delivery().sale_id
        )
        if len(self.order_ids.currency_id) > 1:
            raise UserError(
                self.env._(
                    "These transfers are for orders that are paid on delivery,"
                    " and the amounts still due are in different currencies."
                    " Validate the transfers one currency at a time to collect them."
                )
            )

    @api.depends('order_ids')
    def _compute_amount_to_collect(self):
        self.amount_to_collect = sum(order.amount_unpaid for order in self.order_ids)

    def action_proceed(self):
        """Acknowledge the amount still due and resume the picking validation.

        This is only a confirmation that the money has been (or will be) collected: no payment
        is registered here. The payment is recorded later, when it is settled in the PoS.
        """
        if pickings := self._get_pickings_to_validate():
            return pickings.with_context(skip_pay_on_delivery_notice=True).button_validate()
        return True

    def _get_pickings_to_validate(self):
        return self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
