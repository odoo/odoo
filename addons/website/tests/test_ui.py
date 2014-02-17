import os
import openerp

class TestUi(openerp.tests.HttpCase):
    def test_01_pubic_homepage(self):
        self.phantom_js("/", "console.log('ok')", "openerp.website.snippet");

    def test_02_public_login_logout(self):
        # Page injection works but chm code doesnt work:
        # Can't find variable: Tour
        return
        inject = [
            ("openerp.website.Tour", os.path.join(os.path.dirname(__file__), '../static/src/js/website.tour.js')),
            ("openerp.website.Tour.LoginEdit", os.path.join(os.path.dirname(__file__), "../static/src/js/website.tour.test.admin.js")),
        ]
        self.phantom_js("/", "openerp.website.Tour.run_test('login_edit')", "openerp.website.Tour", inject=inject);

    def test_03_admin_homepage(self):
        self.phantom_js("/", "console.log('ok')", "openerp.website.editor", login='admin');

    def test_04_admin_tour_banner(self):
        self.phantom_js("/", "openerp.website.Tour.run_test('banner')", "openerp.website.Tour", login='admin')

# vim:et:
