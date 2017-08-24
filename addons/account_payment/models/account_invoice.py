# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'account.invoice'

    payment_tx_id = fields.Many2one(
        'payment.transaction', string='Last Transaction',
        copy=False)
    payment_acquirer_id = fields.Many2one(
        'payment.acquirer', string='Payment Acquirer',
        related='payment_tx_id.acquirer_id', store=True)
    payment_tx_count = fields.Integer(
        string="Number of payment transactions",
        compute='_compute_payment_tx_count')

    def _compute_payment_tx_count(self):
        tx_data = self.env['payment.transaction'].read_group(
            [('account_invoice_id', 'in', self.ids)],
            ['account_invoice_id'], ['account_invoice_id']
        )
        mapped_data = dict([(m['sale_order_id'][0], m['sale_order_id_count']) for m in tx_data])
        for invoice in self:
            invoice.payment_tx_count = mapped_data.get(invoice.id, 0)

    def action_view_transactions(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Payment Transactions',
            'res_model': 'payment.transaction',
        }
        tx = self.env['payment.transaction'].search[('account_invoice_id', 'in', self.ids)]
        if len(tx) == 1:
            action.update({
                'res_id': tx.ids[0],
                'view_mode': 'form',
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('account_invoice_id', 'in', self.ids)],
            })
        return action
