from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_ar_supplier_withholding_taxes_ids = fields.Many2many(
        'account.tax', 'product_supplier_withholding_taxes_rel', 'prod_id', 'tax_id',
        string='Vendor Withholding Taxes', help='Default withholding taxes used when paying this product.',
        domain=[('type_tax_use', '=', 'none'), ('l10n_ar_withholding', '=', 'supplier')])
