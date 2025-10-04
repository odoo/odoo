# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _is_pe_company(self):
        return self.company_id.country_code == "PE"

    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        if self._is_pe_company():
            models = ["l10n_latam.identification.type", "l10n_pe.res.city.district", "res.city"]
            res += [model for model in models if model not in res]
        return res

    def _loader_params_res_partner(self):
        vals = super()._loader_params_res_partner()
        if self._is_pe_company():
            vals["search_params"]["fields"] += ["city_id", "l10n_latam_identification_type_id", "l10n_pe_district"]
        return vals

    def _pos_data_process(self, loaded_data):
        res = super()._pos_data_process(loaded_data)
        if self._is_pe_company():
            loaded_data["consumidor_final_anonimo_id"] = self.env.ref("l10n_pe_pos.partner_pe_cf").id
        return res

    def _get_pos_ui_res_city(self, params):
        return self.env["res.city"].search_read(**params["search_params"])

    def _loader_params_res_city(self):
        return {"search_params": {"domain": [], "fields": ["name", "country_id", "state_id"]}}

    def _get_pos_ui_l10n_pe_res_city_district(self, params):
        return self.env["l10n_pe.res.city.district"].search_read(**params["search_params"])

    def _loader_params_l10n_pe_res_city_district(self):
        return {"search_params": {"domain": [], "fields": ["name", "city_id", "country_id", "state_id"]}}

    def _get_pos_ui_l10n_latam_identification_type(self, params):
        return self.env["l10n_latam.identification.type"].search_read(**params["search_params"])

    def _loader_params_l10n_latam_identification_type(self):
        """filter only identification types used in Peru"""
        return {
            "search_params": {
                "domain": [
                    ("l10n_pe_vat_code", "!=", False),
                    ("active", "=", True),
                ],
                "fields": ["name"],
            },
        }
