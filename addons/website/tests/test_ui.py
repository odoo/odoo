import openerp.tests


class TestUi(openerp.tests.HttpCase):
    def test_01_public_homepage(self):
        self.phantom_js("/", "console.log('ok')", "openerp.website.snippet")
        self.chrome_js("/", "console.log('ok')", "openerp.website.snippet")

    def test_03_admin_homepage(self):
        return
        self.phantom_js("/", "console.log('ok')", "openerp.website.editor", login='admin')

    def test_04_admin_tour_banner(self):
        return
        self.phantom_js("/", "openerp.Tour.run('banner', 'test')", "openerp.Tour.tours.banner", login='admin')

# vim:et:
