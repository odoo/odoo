from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_lt_tax_code = fields.Char(string='Tax Code', help='The Lithuanian tax system has a code for standard taxes, to use in iSAF and SAFT.')
