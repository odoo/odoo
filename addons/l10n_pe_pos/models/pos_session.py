# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _is_pe_company(self):
        return self.company_id.country_code == "PE"

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)

        if not self._is_pe_company():
            return params
        params['res.partner']['fields'] += ["city_id", "l10n_latam_identification_type_id", "l10n_pe_district"]
        params['l10n_pe.res.city.district'] = {
            'domain': [],
            'fields': ["name", "city_id", "country_id", "state_id"],
        }
        params['res.city'] = {
            'domain': [],
            'fields': ["name", "country_id", "state_id"],
        }
        params['l10n_latam.identification.type'] = {
            'domain': [("l10n_pe_vat_code", "!=", False), ('country_id', 'in', [self.company_id.country_id.id, False])],
            'fields': ['name'],
        }

        return params

    def load_data(self, models_to_load, only_data=False):
        response = super().load_data(models_to_load, only_data)
        if not only_data and self._is_pe_company():
            response['custom']['consumidor_final_anonimo_id'] = self.env.ref('l10n_pe_pos.partner_pe_cf').id
            response['custom']['default_l10n_latam_identification_type_id'] = self.env.ref('l10n_pe.it_DNI').id
        return response
