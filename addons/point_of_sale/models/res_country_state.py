from odoo import api, models


class ResCountryState(models.Model):
    _name = "res.country.state"
    _inherit = ["res.country.state", "mixin.pos.load"]

    @api.model
    def _get_referenced_state_ids(self, data, config):
        state_ids = self._get_referenced_ids(data, "res.partner", "state_id")
        state_ids.add(config.company_id.state_id.id)
        state_ids.discard(False)
        return state_ids

    @api.model
    def _load_pos_data_domain(self, data, config):
        country_ids = self.env["res.country"]._get_referenced_country_ids(data, config)
        state_ids = self._get_referenced_state_ids(data, config)
        return [
            "|",
            ("country_id", "in", list(country_ids)),
            ("id", "in", list(state_ids)),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return ["id", "name", "code", "country_id"]
