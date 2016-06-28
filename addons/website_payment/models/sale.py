# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
