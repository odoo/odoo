# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.lunch.tests.common import TestsCommon


class TestLunchProductReport(TestsCommon):
    def test_product_available(self):
        self.assertTrue(self.env['lunch.product.report'].search([]), 'There should be some record on lunch_product_report')
