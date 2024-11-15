from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_edi_verifactu_required = fields.Boolean(
        related='company_id.l10n_es_edi_verifactu_required',
        readonly=False,
    )
    l10n_es_edi_verifactu_required_readonly = fields.Boolean(
        compute="_compute_l10n_es_edi_verifactu_required_readonly",
    )
    l10n_es_edi_verifactu_certificate_ids = fields.One2many(
        related='company_id.l10n_es_edi_verifactu_certificate_ids',
        readonly=False,
    )
    l10n_es_edi_verifactu_test_environment = fields.Boolean(
        related='company_id.l10n_es_edi_verifactu_test_environment',
        readonly=False,
    )

    def _compute_l10n_es_edi_verifactu_required_readonly(self):
        for config in self:
            record_document_count = self.env['l10n_es_edi_verifactu.record_document'].search_count([
                ('company_id', "=", config.company_id.id),
            ], limit=1)
            config.l10n_es_edi_verifactu_required_readonly = record_document_count > 0
