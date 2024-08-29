from odoo import fields, models
from odoo.addons import base


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    l10n_in_withholding_account_id = fields.Many2one(
        related='company_id.l10n_in_withholding_account_id',
        readonly=False,
    )
    l10n_in_withholding_journal_id = fields.Many2one(
        related='company_id.l10n_in_withholding_journal_id',
        readonly=False,
    )
