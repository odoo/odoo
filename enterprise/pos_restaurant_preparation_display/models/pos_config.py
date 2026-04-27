# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.tools import convert


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _load_preparation_display_data(self):
        main_company = self.env.ref('base.main_company', raise_if_not_found=False)
        is_main_company = main_company and self.env.company.id == main_company.id
        is_demo_not_yet_loaded = self.env.ref('pos_restaurant.pos_config_main_restaurant', raise_if_not_found=False) and not self.env.ref('pos_preparation_display.preparation_display_main_restaurant', raise_if_not_found=False)
        if is_main_company and is_demo_not_yet_loaded:
            convert.convert_file(self.env, 'pos_restaurant_preparation_display', 'data/main_restaurant_preparation_display_data.xml', None, noupdate=True, mode='init', kind='data')
            if self.env.ref('pos_restaurant.food', raise_if_not_found=False) and self.env.ref('pos_restaurant.pos_closed_order_3_1', raise_if_not_found=False):
                convert.convert_file(self.env, 'pos_restaurant_preparation_display', 'data/pos_restaurant_preparation_display_demo.xml', None, noupdate=True, mode='init', kind='data')

    @api.model
    def load_onboarding_restaurant_scenario(self):
        super().load_onboarding_restaurant_scenario()
        self._load_preparation_display_data()
