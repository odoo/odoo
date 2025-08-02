from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_gcc_dual_language_receipt = fields.Boolean(string='GCC Formatted Receipts', compute="_compute_l10n_gcc_dual_language_receipt", store=True, readonly=False)

    @api.depends("company_id.country_id.code")
    def _compute_l10n_gcc_dual_language_receipt(self):
        gcc_configs = self.filtered(lambda rec: rec.company_id.country_code in ['SA', 'AE', 'KW', 'QA'])
        gcc_configs.l10n_gcc_dual_language_receipt = True
        (self - gcc_configs).l10n_gcc_dual_language_receipt = False
