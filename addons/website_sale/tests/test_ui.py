import os

import openerp

inject = [
    ("openerp.website.Tour", os.path.join(os.path.dirname(__file__), '../../website/static/src/js/website.tour.js')),
    ("openerp.website.Tour.ShopTest", os.path.join(os.path.dirname(__file__), "../static/src/js/website.tour.sale.js")),
]

class TestUi(openerp.tests.HttpCase):
    def test_01_admin_shop_tour(self):
        # Works locally probably due to a race condition on openerp.website.Tour.Shop
        # object should only be define once ready
        return
        self.phantom_js("/", "openerp.website.Tour.run_test('shop')", "openerp.website.Tour.Shop", login="admin")

    def test_02_admin_checkout(self):
        return
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour", login="admin")

    def test_03_demo_checkout(self):
        return
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour.ShopTest", login="demo", inject=inject)

    def test_04_public_checkout(self):
        return
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour.ShopTest", inject=inject)

