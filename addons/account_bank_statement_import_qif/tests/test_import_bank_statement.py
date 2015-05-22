from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestQifFile(TransactionCase):
    """Tests for import bank statement qif file format (account.bank.statement.import)
    """

    def setUp(self):
        super(TestQifFile, self).setUp()
        self.BankStatementImport = self.env['account.bank.statement.import']
        self.BankStatement = self.env['account.bank.statement']
        self.BankStatementLine = self.env['account.bank.statement.line']

    def test_qif_file_import(self):
        from openerp.tools import float_compare
        qif_file_path = get_module_resource('account_bank_statement_import_qif', 'test_qif_file', 'test_qif.qif')
        qif_file = open(qif_file_path, 'rb').read().encode('base64')
        bank_statement_id = self.BankStatementImport.create(dict(
            data_file=qif_file,
        ))
        company = self.env.user.company_id
        journal_vals = self.env['account.journal']._prepare_bank_journal(company, {'account_type': 'bank', 'acc_name': 'Bank Account (test import qif)'})
        journal = self.env['account.journal'].create(journal_vals)
        bank_statement_id.with_context(journal_id=journal.id).import_file()
        line = self.BankStatementLine.search([('name', '=', 'YOUR LOCAL SUPERMARKET')], limit=1)
        assert float_compare(line.statement_id.balance_end_real, -1896.09, 2) == 0
