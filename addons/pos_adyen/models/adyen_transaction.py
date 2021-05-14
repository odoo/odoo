# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AdyenTransaction(models.Model):
    _inherit = 'adyen.transaction'

    pos_payment_id = fields.Many2one('pos.payment', string='POS Order')
    pos_order_id = fields.Many2one(related='pos_payment_id.pos_order_id')

    def _post_transaction_sync(self):
        to_match = self.filtered(lambda t: not t.pos_payment_id)
        pos_payment_ids = self.env['pos.payment'].search([('transaction_id', 'in', to_match.mapped('reference'))])

        for tx in to_match:
            tx.pos_payment_id = pos_payment_ids.filtered(lambda t: t.transaction_id == tx.reference)
