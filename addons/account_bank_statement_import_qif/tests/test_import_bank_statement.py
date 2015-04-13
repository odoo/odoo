# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestQifFile(TransactionCase):
    """Tests for import bank statement qif file format
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestQifFile, self).setUp()
        self.statement_import_model = self.env['account.bank.statement.import']
        self.statement_line_model = self.env['account.bank.statement.line']

    def test_qif_file_import(self):
        from openerp.tools import float_compare
        qif_file_path = get_module_resource(
            'account_bank_statement_import_qif',
            'test_qif_file', 'test_qif.qif')
        qif_file = open(qif_file_path, 'rb').read().encode('base64')
        bank_statement_improt = self.statement_import_model.with_context(
            journal_id=self.ref('account.bank_journal')).create(
            dict(data_file=qif_file))
        bank_statement_improt.import_file()
        bank_statement = self.statement_line_model.search(
            [('name', '=', 'YOUR LOCAL SUPERMARKET')], limit=1)[0].statement_id
        assert float_compare(bank_statement.balance_end_real, -1896.09, 2) == 0
