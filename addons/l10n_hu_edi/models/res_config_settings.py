# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_hu_tax_regime = fields.Selection(
        related='company_id.l10n_hu_tax_regime',
        readonly=False,
    )
    l10n_hu_edi_server_mode = fields.Selection(
        related='company_id.l10n_hu_edi_server_mode',
        readonly=False,
    )
    l10n_hu_edi_username = fields.Char(
        related='company_id.l10n_hu_edi_username',
        readonly=False,
    )
    l10n_hu_edi_password = fields.Char(
        related='company_id.l10n_hu_edi_password',
        readonly=False,
    )
    l10n_hu_edi_signature_key = fields.Char(
        related='company_id.l10n_hu_edi_signature_key',
        readonly=False,
    )
    l10n_hu_edi_replacement_key = fields.Char(
        related='company_id.l10n_hu_edi_replacement_key',
        readonly=False,
    )
    # Technical field to control display of the "Authentication with NAV 3.0 successful" banner
    l10n_hu_edi_is_active = fields.Boolean(
        compute='_compute_l10n_hu_edi_is_active',
    )

    @api.depends('company_id.l10n_hu_edi_server_mode')
    def _compute_l10n_hu_edi_is_active(self):
        for record in self:
            record.l10n_hu_edi_is_active = record.company_id.l10n_hu_edi_server_mode in ['production', 'test']

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.company_id.l10n_hu_edi_server_mode in ['production', 'test']:
                record.company_id._l10n_hu_edi_test_credentials()
        return records
