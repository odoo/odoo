from odoo import api, models


class ResCountry(models.Model):
    _name = "res.country"
    _inherit = ["res.country", "mixin.pos.load"]

    @api.model
    def _get_referenced_country_ids(self, data, config):
        country_ids = self._get_referenced_ids(data, "res.partner", "country_id")
        country_ids.add(config.company_id.country_id.id)
        country_ids.add(
            config.company_id.account_config_id.account_fiscal_country_id.id
        )
        states = self.env["res.country.state"]
        state_ids = states._get_referenced_state_ids(data, config)
        country_ids.update(
            states.search([("id", "in", list(state_ids))]).country_id.ids
        )
        country_ids.discard(False)
        return country_ids

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("id", "in", list(self._get_referenced_country_ids(data, config)))]

    @api.model
    def _load_pos_data_fields(self, config):
        return ["id", "name", "code", "vat_label"]
