from odoo import fields, models
from odoo.addons import account


class AccountAccount(account.AccountAccount):

    l10n_in_tds_tcs_section_id = fields.Many2one('l10n_in.section.alert', string="TCS/TDS Section")
