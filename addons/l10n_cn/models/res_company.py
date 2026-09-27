from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_cn_output_vat_offset_account_id = fields.Many2one(
        comodel_name='account.account',
        domain="[('account_type', '=', 'liability_current')]",
        string="Output VAT Offset Account",
    )
    l10n_cn_output_vat_offset_journal_id = fields.Many2one(
        comodel_name='account.journal',
        domain="[('type', '=', 'general')]",
        string="Output VAT Offset Journal",
    )
    l10n_cn_vat_differential_taxation = fields.Boolean(
        string="VAT Differential Taxation"
    )
