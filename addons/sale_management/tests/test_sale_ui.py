# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCase):

    def test_01_sale_tour(self):
        self.start_tour("/web", 'sale_tour', login="admin", step_delay=100)

    def test_02_sale_tour_company_onboarding_done(self):
        self.env.company.set_onboarding_step_done('base_onboarding_company_state')
        self.start_tour("/web", 'sale_tour', login="admin", step_delay=100)

    def test_03_sale_quote_tour(self):
        self.start_tour("/web", 'sale_quote_tour', login="admin", step_delay=100)
