# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.http import request


class SaleOrderDigital(models.Model):

    _inherit = 'sale.order'

    @api.multi
    def get_purchased_digital_content(self):
        self.ensure_one()
        if self.payment_state == 'done':
            return self.order_line.mapped('product_id').get_digital_attachment()
        else:
            products = request.env['account.invoice.line'].sudo().search(
                [('invoice_id', 'in', self.invoice_ids.ids), ('invoice_id.state', '=', 'paid')]).mapped('product_id')
            return products.get_digital_attachment()
