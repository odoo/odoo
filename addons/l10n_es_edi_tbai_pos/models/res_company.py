from odoo import api, models
from odoo.addons import point_of_sale, l10n_es_edi_tbai


class ResCompany(l10n_es_edi_tbai.ResCompany, point_of_sale.ResCompany):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['l10n_es_tbai_is_enabled']
