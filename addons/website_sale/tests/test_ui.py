import os

import unittest2

import openerp.tests


class TestUi(openerp.tests.HttpCase):
    def test_01_admin_shop_tour(self):
        return
        self.phantom_js("/", "openerp.website.Tour.run_test('shop')", "openerp.website.Tour.Shop", login="admin")

    def test_02_admin_checkout(self):
        return
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour.ShopTest", login="admin")

    def test_03_demo_checkout(self):
        return
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour.ShopTest", login="demo")

    def test_04_public_checkout(self):
        return
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour.ShopTest")
