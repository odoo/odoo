import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_bank_statement_reconciliation(self):
        self.phantom_js("/web",
            "odoo.__DEBUG__.services['web_tour.tour'].run('bank_statement_reconciliation')",
            "odoo.__DEBUG__.services['web_tour.tour'].tours.bank_statement_reconciliation.ready", login="admin")
