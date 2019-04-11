# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_01_admin_shop_tour(self):
        self.start_tour("/", 'shop', login="admin")

    def test_02_admin_checkout(self):
        self.start_tour("/", 'shop_buy_product', login="admin")

    def test_03_demo_checkout(self):
        self.start_tour("/", 'shop_buy_product', login="demo")

    # TO DO - add public test with new address when convert to web.tour format.
