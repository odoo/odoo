from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['l10n_es_edi_verifactu_required']

    def _l10n_es_get_pos_edi_mode(self):
        self.ensure_one()
        return 'verifactu' if self.l10n_es_edi_verifactu_required else super()._l10n_es_get_pos_edi_mode()
