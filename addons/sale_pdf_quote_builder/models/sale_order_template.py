# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    sale_header = fields.Binary(
        string="Header pages", default=lambda self: self.env.company.sale_header)
    sale_footer = fields.Binary(
        string="Footer pages", default=lambda self: self.env.company.sale_footer)
