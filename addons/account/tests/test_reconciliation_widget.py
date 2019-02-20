import logging
import odoo.tests
import time
from odoo.addons.account.tests.test_reconciliation import TestReconciliation

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_bank_statement_reconciliation(self):
        bank_stmt_name = 'BNK/%s/0001' % time.strftime('%Y')
        bank_stmt = self.env['account.bank.statement'].search([('name', '=', bank_stmt_name)])
        if not bank_stmt:
             _logger.exception('Could not find bank statement %s' % bank_stmt_name)

        # To be able to test reconciliation, admin user must have access to accounting features, so we give him the right group for that
        self.env.ref('base.user_admin').write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})

        self.phantom_js("/web#statement_ids=" + str(bank_stmt.id) + "&action=bank_statement_reconciliation_view",
            "odoo.__DEBUG__.services['web_tour.tour'].run('bank_statement_reconciliation')",
            "odoo.__DEBUG__.services['web_tour.tour'].tours.bank_statement_reconciliation.ready", login="admin")


@odoo.tests.tagged('post_install', '-at_install')
class TestReconciliationWidget(TestReconciliation):

    def test_statement_suggestion_other_currency(self):
        # company currency is EUR
        # payment in USD
        invoice = self.create_invoice(invoice_amount=50, currency_id=self.currency_usd_id)

        # journal currency in USD
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': self.bank_journal_usd.id,
            'date': time.strftime('%Y-07-15'),
            'name': 'payment %s' % invoice.number,
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': 50,
            'date': time.strftime('%Y-07-15'),
        })

        result = self.env['account.reconciliation.widget'].get_bank_statement_line_data(bank_stmt_line.ids)
        self.assertEqual(result['lines'][0]['reconciliation_proposition'][0]['amount_str'], '$ 50.00')