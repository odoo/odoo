from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_cn_output_vat_offset_account_id = fields.Many2one(
        related="company_id.l10n_cn_output_vat_offset_account_id",
        readonly=False,
    )
    l10n_cn_output_vat_offset_journal_id = fields.Many2one(
        related="company_id.l10n_cn_output_vat_offset_journal_id",
        readonly=False,
    )
    l10n_cn_vat_differential_taxation = fields.Boolean(
        related='company_id.l10n_cn_vat_differential_taxation',
        readonly=False,
    )
