from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_pos_ui_pos_config(self, params):
        config = super()._get_pos_ui_pos_config(params)
        if config.get('l10n_es_edi_verifactu_required'):
            simplified_invoice_limit = self.env['ir.config_parameter'].sudo().get_param(
                'l10n_es_edi_verifactu_pos.simplified_invoice_limit',
                '400'
            )
            config['l10n_es_edi_verifactu_simplified_invoice_limit'] = float(simplified_invoice_limit)
        return config
