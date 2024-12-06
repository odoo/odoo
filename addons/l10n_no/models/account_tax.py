from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_no_standard_code = fields.Char(string='Standard Tax Code', help='The Norwegian tax system has a code for standard taxes, to use when reporting to them.')
