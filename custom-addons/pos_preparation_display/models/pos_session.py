# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        models_to_load = super()._pos_ui_models_to_load()
        models_to_load.append('pos_preparation_display.display')

        return models_to_load

    def _get_pos_ui_pos_preparation_display_display(self, params):
        preparation_displays = self.env['pos_preparation_display.display'].search(**params['search_params'])
        p_dis_for_ui = []

        for p_dis in preparation_displays:
            p_dis_for_ui.append({
                'id': p_dis.id,
                'pdis_category_ids': p_dis._get_pos_category_ids().ids,
            })

        return p_dis_for_ui

    def _loader_params_pos_preparation_display_display(self):
        # for the domain refer at _get_pos_ui_pos_preparation_display_display
        return {
            'search_params': {
                'domain': ['|', ('pos_config_ids', '=', self.config_id.id), ('pos_config_ids', '=', False)]
            }
        }

    def get_onboarding_data(self):
        result = super().get_onboarding_data()
        result.update({'pos_preparation_display.display' : self._load_model('pos_preparation_display.display')})
        return result
