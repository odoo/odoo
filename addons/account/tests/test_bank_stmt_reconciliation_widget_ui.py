from odoo.tests import HttpCase

class TestUi(HttpCase):
    post_install = True
    at_install = False

    def test_01_admin_bank_statement_reconciliation(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('bank_statement_reconciliation', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.bank_statement_reconciliation", login="admin")
