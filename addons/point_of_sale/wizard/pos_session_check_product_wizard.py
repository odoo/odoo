# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import convert


class PosSessionCheckProductWizard(models.TransientModel):
    _name = 'pos.session.check_product_wizard'
    _description = 'Verify if there are any products for the PoS'

    def load_demo_products(self):
        convert.convert_file(self.env.cr, 'point_of_sale', 'data/point_of_sale_onboarding.xml', None, mode='init', kind='data')
        return self.open_ui()

    def open_ui(self):
        config = self.env['pos.config'].browse(self.env.context.get('config_id'))
        return config._action_to_open_ui()
