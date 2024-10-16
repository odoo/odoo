from odoo import api, models
from odoo.addons import point_of_sale, l10n_es


class ResCompany(point_of_sale.ResCompany, l10n_es.ResCompany):

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == "ES":
            params += ["street", "city", "zip", "l10n_es_simplified_invoice_limit"]
        return params
