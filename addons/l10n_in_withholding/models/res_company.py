from odoo import fields, models
from odoo.addons import base


class ResCompany(models.Model, base.ResCompany):

    l10n_in_withholding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="TDS Account",
        check_company=True,
        domain="[('type', '=', 'general')]"
    )
    l10n_in_withholding_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="TDS Journal",
        check_company=True,
    )
