# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ------------------
    # Fields declaration
    # ------------------

    taxes_id = fields.Many2many(domain=['|', ('type_tax_use', '=', 'sale'), ('l10n_account_withholding_type', '=', 'customer')])
    supplier_taxes_id = fields.Many2many(domain=['|', ('type_tax_use', '=', 'purchase'), ('l10n_account_withholding_type', '=', 'supplier')])
