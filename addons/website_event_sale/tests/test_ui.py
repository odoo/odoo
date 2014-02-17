import openerp

inject = [
    "./../../../website/static/src/js/website.tour.test.js",
    "./../../../website_event_sale/static/src/js/website.tour.event_sale.js",
]

class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "openerp.website.Tour.run_test('banner')", "openerp.website.Tour")

    def test_demo(self):
        self.phantom_js("/", "openerp.website.Tour.run_test('login_edit')", "openerp.website.Tour", login="demo", password="demo", inject=inject);

    def test_public(self):
        self.phantom_js("/", "openerp.website.Tour.run_test('login_edit')", "openerp.website.Tour", login=None, inject=inject);

