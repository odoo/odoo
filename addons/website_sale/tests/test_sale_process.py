import os

import openerp.tests

inject = [
    ("openerp.website.Tour", os.path.join(os.path.dirname(__file__), '../../website/static/src/js/website.tour.js')),
    ("openerp.website.Tour.ShopTest", os.path.join(os.path.dirname(__file__), "../static/src/js/website.tour.sale.js")),
]

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_admin_shop_tour(self):
        self.phantom_js("/", "openerp.website.Tour.run('shop', 'test')", "openerp.website.Tour.tours.shop", login="admin")

    def test_02_admin_checkout(self):
        self.phantom_js("/", "openerp.website.Tour.run('shop_customize', 'test')", "openerp.website.Tour.tours.shop_customize", login="admin", inject=inject)
        self.phantom_js("/", "openerp.website.Tour.run('shop_buy_product', 'test')", "openerp.website.Tour.tours.shop_buy_product", login="admin", inject=inject)

    def test_03_demo_checkout(self):
        self.phantom_js("/", "openerp.website.Tour.run('shop_buy_product', 'test')", "openerp.website.Tour.tours.shop_buy_product", login="demo", inject=inject)

    def test_04_public_checkout(self):
        self.phantom_js("/", "openerp.website.Tour.run('shop_buy_product', 'test')", "openerp.website.Tour.tours.shop_buy_product", inject=inject)
