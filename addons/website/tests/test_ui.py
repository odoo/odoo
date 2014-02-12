import openerp

class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "console.log('ok')", "window.openerp.website")
        self.phantom_js("/", "openerp.website.Tour.run_test('banner')", "openerp.website.Tour")

    def test_public(self):
        inject = [
            "./../../../website/static/src/js/website.tour.test.js",
            "./../../../website/static/src/js/website.tour.test.admin.js"i
        ]
        self.phantom_js("/", "openerp.website.Tour.run_test('login_edit')", "openerp.website.Tour", inject=inject);

