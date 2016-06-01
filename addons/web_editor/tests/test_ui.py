import openerp.tests
from openerp.api import Environment


class TestUi(openerp.tests.HttpCase):
    def test_01_admin_rte(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web.Tour'].run('rte', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.rte", login='admin')

    def test_02_admin_rte_inline(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web.Tour'].run('rte_inline', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.rte", login='admin')

    def test_02_admin_snippets(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web.Tour'].run('web_editor_snippets', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.web_editor_snippets", login='admin')
