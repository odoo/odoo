from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['l10n_es_tbai_is_enabled']

    def _l10n_es_get_pos_edi_mode(self):
        self.ensure_one()
        return 'tbai' if self.l10n_es_tbai_is_enabled else super()._l10n_es_get_pos_edi_mode()
