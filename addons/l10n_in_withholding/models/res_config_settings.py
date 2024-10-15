from odoo import fields, models
from odoo.addons import l10n_in


class ResConfigSettings(l10n_in.ResConfigSettings):

    l10n_in_withholding_account_id = fields.Many2one(
        related='company_id.l10n_in_withholding_account_id',
        readonly=False,
    )
    l10n_in_withholding_journal_id = fields.Many2one(
        related='company_id.l10n_in_withholding_journal_id',
        readonly=False,
    )
