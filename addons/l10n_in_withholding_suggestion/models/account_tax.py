from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_section_id = fields.Many2one('l10n_in.section.alert', string="Section")
