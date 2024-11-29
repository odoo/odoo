from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_in_tds_tcs_section_id = fields.Many2one(related="account_id.l10n_in_tds_tcs_section_id")
