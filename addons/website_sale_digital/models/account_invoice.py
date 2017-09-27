# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountInvoiceLine(models.Model):

    _inherit = ['account.invoice.line']

    def get_digital_purchases(self):
        partner = self.env.user.partner_id

        # Get paid invoices
        purchases = self.sudo().search_read(
            domain=[('invoice_id.state', '=', 'paid'), ('invoice_id.partner_id', '=', partner.id)],
            fields=['product_id'],
        )

        # Get free products
        purchases += self.env['sale.order.line'].sudo().search_read(
            domain=[('price_subtotal', '=', 0.0), ('order_id.partner_id', '=', partner.id)],
            fields=['product_id'],
        )

        # I only want product_ids, but search_read insists in giving me a list of
        # (product_id: <id>, name: <product code> <template_name> <attributes>)
        return purchases.mapped('product_id').ids
