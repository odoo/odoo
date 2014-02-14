import openerp

inject = [
    "./../../../website/static/src/js/website.tour.test.js",
    "./../../../website/static/src/js/website.tour.test.admin.js",
]

class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "openerp.website.Tour.run_test('shop')", "openerp.website.Tour")
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour")

    def test_demo(self):
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour", login="demo", password="demo", inject=inject)

    def test_public(self):
        self.phantom_js("/", "openerp.website.Tour.run_test('shop_buy_product')", "openerp.website.Tour", login=None, inject=inject)

