# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ------------------
    # Fields declaration
    # ------------------

    taxes_id = fields.Many2many(domain=[('type_tax_use', 'in', ['sale', 'sales_wth'])])
    supplier_taxes_id = fields.Many2many(domain=[('type_tax_use', 'in', ['purchase', 'purchases_wth'])])
