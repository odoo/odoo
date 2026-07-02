from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_cn_output_vat_offset_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Output VAT Offset Account",
        related="company_id.l10n_cn_output_vat_offset_account_id",
        domain="[('account_type', '=', 'liability_current')]",
        readonly=False,
    )
    l10n_cn_output_vat_offset_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Output VAT Offset Journal",
        related="company_id.l10n_cn_output_vat_offset_journal_id",
        domain="[('type', '=', 'general')]",
        readonly=False,
    )
