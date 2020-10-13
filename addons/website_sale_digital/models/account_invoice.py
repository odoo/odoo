# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountInvoiceLine(models.Model):

    _inherit = ['account.move.line']

    def get_digital_purchases(self):
        partner = self.env.user.partner_id

        # Get paid invoices
        purchases = self.sudo().search_read(
            domain=[
                ('move_id.payment_state', 'in', ['paid', 'in_payment']),
                ('move_id.partner_id', '=', partner.id),
                ('product_id', '!=', False),
            ],
            fields=['product_id'],
        )

        # Get free products
        purchases += self.env['sale.order.line'].sudo().search_read(
            domain=[('order_id.partner_id', '=', partner.id), '|', ('price_subtotal', '=', 0.0), ('order_id.amount_total', '=', 0.0)],
            fields=['product_id'],
        )

        # I only want product_ids, but search_read insists in giving me a list of
        # (product_id: <id>, name: <product code> <template_name> <attributes>)
        return [line['product_id'][0] for line in purchases]
