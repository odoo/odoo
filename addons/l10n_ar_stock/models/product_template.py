from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_ar_arba_code = fields.Char(
        string="ARBA Code",
        size=6,
        help="Argentina: A six-digit code sourced from the official nomenclature.",
    )
