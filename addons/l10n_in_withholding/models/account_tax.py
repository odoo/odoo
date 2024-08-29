from odoo import fields, models
from odoo.addons import account


class AccountTax(models.Model, account.AccountTax):

    l10n_in_tds_tax_type = fields.Selection([
        ('sale', 'Sale'),
        ('purchase', 'Purchase')
    ], string="TDS Tax Type")
    l10n_in_section_id = fields.Many2one('l10n_in.section.alert', string="Section")
