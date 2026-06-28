# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        """
        Load l10n_latam.identification.type model
        """
        result = super()._pos_ui_models_to_load()
        result.append('l10n_latam.identification.type')
        return result

    def _loader_params_l10n_latam_identification_type(self):
        """
        Params to load l10n_latam.identification.type model
        """
        return {'search_params': {'fields': ['name', 'is_vat', 'country_id']}}

    def _get_pos_ui_l10n_latam_identification_type(self, params):
        """
        Get records to l10n_latam.identification.type model
        """
        identification_type_ids = self.env['l10n_latam.identification.type'].search_read(
            **params['search_params']
        )
        return identification_type_ids

    def _loader_params_res_partner(self):
        """
        Load l10n_latam_identification_type_id in res.partner model
        """
        result = super()._loader_params_res_partner()
        result['search_params']['fields'].append('l10n_latam_identification_type_id')
        return result
