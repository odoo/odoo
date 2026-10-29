# Copyright 2018 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # product_brand_id = fields.Many2one('product.brand', related="product_id.product_brand_id", string='Brand', store=True)
    product_brand_id = fields.Many2one('product.brand', string='Brand', store=True)


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    product_brand_id = fields.Many2one('product.brand', string='Brand')

    def _select(self):
        return super()._select() + ", line.product_brand_id as product_brand_id"
