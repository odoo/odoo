from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Veri*Factu Required",
        compute="_compute_l10n_es_edi_verifactu_required",
    )

    def _compute_l10n_es_edi_verifactu_required(self):
        for config in self:
            config.l10n_es_edi_verifactu_required = config.company_id._l10n_es_pos_get_fiscal_mode() == 'verifactu'
