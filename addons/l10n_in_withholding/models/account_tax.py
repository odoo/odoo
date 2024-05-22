from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_tds_tax_type = fields.Selection([
        ('sale', 'Sale'),
        ('purchase', 'Purchase')
    ], string="TDS Tax Type")
