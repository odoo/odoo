from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_lt_tax_code = fields.Char(
        string='Tax Code',
        help="The tax code according to the VAT classification",
    )
