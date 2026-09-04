# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class PayOnDelivery(models.TransientModel):
    _name = 'pay.on.delivery'
    _description = "Pay on Delivery"

    order_ids = fields.Many2many(comodel_name='sale.order', compute='_compute_order_ids')
    amount_on_delivery = fields.Monetary(compute='_compute_amount_on_delivery')
    currency_id = fields.Many2one(related='order_ids.currency_id')

    @api.depends_context('button_validate_picking_ids')
    def _compute_order_ids(self):
        self.order_ids = (
            self._get_pickings_to_validate()._filtered_pending_delivery_payment().sale_id
        )
        if len(self.order_ids.currency_id) > 1:
            raise UserError(
                self.env._(
                    "These transfers are for orders that are paid on delivery,"
                    " and the amounts still due are in different currencies."
                    " Validate the transfers one currency at a time to collect them."
                )
            )

    @api.depends("order_ids")
    def _compute_amount_on_delivery(self):
        self.amount_on_delivery = sum(order.amount_unpaid for order in self.order_ids)

    def action_confirm_payment(self):
        if pickings := self._get_pickings_to_validate():
            return pickings.with_context(amount_on_delivery_collected=True).button_validate()
        return True

    def _get_pickings_to_validate(self):
        return self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
