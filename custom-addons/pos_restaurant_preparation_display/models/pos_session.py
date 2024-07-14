# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.tools import convert

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_onboarding_data(self):
        super()._load_onboarding_data()
        restaurant_config = self.env.ref('pos_restaurant.pos_config_main_restaurant', raise_if_not_found=False)
        if restaurant_config:
            convert.convert_file(self.env, 'pos_restaurant_preparation_display', 'data/pos_restaurant_preparation_display_onboarding.xml', None, mode='init', kind='data')
