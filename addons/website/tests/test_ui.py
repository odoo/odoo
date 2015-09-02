import openerp.tests


class TestUi(openerp.tests.HttpCase):
    def test_01_public_homepage(self):
        self.phantom_js("/", "console.log('ok')", "'website.snippets.animation' in odoo.__DEBUG__.services")

    def test_02_admin_homepage(self):
        self.phantom_js("/", "console.log('ok')", "'website.snippets.editor' in odoo.__DEBUG__.services", login='admin')

    def test_03_admin_tour_banner(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('banner', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.banner", login='admin')

    def test_03_admin_tour_rte_translator(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('rte_translator', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.rte_translator", login='admin')
