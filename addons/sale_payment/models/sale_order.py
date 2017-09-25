# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_tx_ids = fields.One2many('payment.transaction', 'sale_order_id', string='Transactions')
    payment_tx_id = fields.Many2one('payment.transaction', string='Last Transaction', copy=False)
    payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', related='payment_tx_id.acquirer_id', store=True)
    payment_transaction_count = fields.Integer(
        string="Number of payment transactions",
        compute='_compute_payment_transaction_count')

    def _compute_payment_transaction_count(self):
        transaction_data = self.env['payment.transaction'].read_group([('sale_order_id', 'in', self.ids)], ['sale_order_id'], ['sale_order_id'])
        mapped_data = dict([(m['sale_order_id'][0], m['sale_order_id_count']) for m in transaction_data])
        for order in self:
            order.payment_transaction_count = mapped_data.get(order.id, 0)

    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    def action_view_transaction(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Payment Transactions',
            'res_model': 'payment.transaction',
        }
        if self.payment_transaction_count == 1:
            action.update({
                'res_id': self.env['payment.transaction'].search([('sale_order_id', '=', self.id)]).id,
                'view_mode': 'form',
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('sale_order_id', '=', self.id)],
            })
        return action
