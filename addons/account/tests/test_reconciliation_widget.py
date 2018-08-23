import logging
import odoo.tests

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_bank_statement_reconciliation(self):
        bank_stmt = self.env['account.bank.statement'].search([('name', '=', 'BNK/2014/001')])
        if not bank_stmt:
             _logger.exception('Could not find bank statement BNK/2014/001')

        self.phantom_js("/web#statement_ids=" + str(bank_stmt.id) + "&action=bank_statement_reconciliation_view",
            "odoo.__DEBUG__.services['web_tour.tour'].run('bank_statement_reconciliation')",
            "odoo.__DEBUG__.services['web_tour.tour'].tours.bank_statement_reconciliation.ready", login="admin")
