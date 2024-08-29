from odoo import api, models
from odoo.addons import base


class ResCompany(models.Model, base.ResCompany):

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == "ES":
            params += ["street", "city", "zip"]
        return params
