# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase


class TestOnboarding(HttpCase):
    def test_01_get_sample_sales_order_from_scratch(self):
        # Make sure there are no QO nor products
        if 'loyalty.reward' in self.env:
            self.env['loyalty.reward'].search([]).active = False
        self.env['sale.order'].search([
            ('company_id', '=', self.env.company.id),
            ('partner_id', '=', self.env.user.partner_id.id),
            ('state', '=', 'draft')
        ]).state = 'cancel'
        self.env['product.product'].search([]).active = False
        self.env['onboarding.onboarding.step']._get_sample_sales_order()
