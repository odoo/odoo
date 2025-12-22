from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    l10n_in_tds_tcs_section_id = fields.Many2one('l10n_in.section.alert', string="TCS/TDS Section")
