import openerp.tests


class TestUi(openerp.tests.HttpCase):
    def test_01_public_homepage(self):
        self.phantom_js("/", "console.log('ok')", "odoo.__DEBUG__.services['website.snippets.animation']")

    def test_02_admin_homepage(self):
        self.phantom_js("/", "console.log('ok')", "odoo.__DEBUG__.services['website.snippets.editor']", login='admin')

    def test_03_admin_rte(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('website_rte', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.website_rte", login='admin')

    def test_04_admin_tour_banner(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('banner', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.banner", login='admin')
