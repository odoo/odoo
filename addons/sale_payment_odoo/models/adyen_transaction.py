# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AdyenTransaction(models.Model):
    _inherit = 'adyen.transaction'

    sale_order_ids = fields.Many2many(related='payment_transaction_id.sale_order_ids')
    sale_order_ids_nbr = fields.Integer(related='payment_transaction_id.sale_order_ids_nbr')

    def action_view_sales_orders(self):
        return self.payment_transaction_id.action_view_sales_orders()
