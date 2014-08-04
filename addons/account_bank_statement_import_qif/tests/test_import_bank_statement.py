from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource

class TestQifFile(TransactionCase):
    """Tests for import bank statement qif file format (account.bank.statement.import)
    """

    def setUp(self):
        super(TestQifFile, self).setUp()
        self.statement_import_model = self.registry('account.bank.statement.import')
        self.bank_statement_model = self.registry('account.bank.statement')
        self.bank_statement_line_model = self.registry('account.bank.statement.line')

    def test_qif_file_import(self):
        from openerp.tools import float_compare
        cr, uid = self.cr, self.uid
        qif_file_path = get_module_resource('account_bank_statement_import_qif', 'test_qif_file', 'test_qif.qif')
        qif_file = open(qif_file_path, 'rb').read().encode('base64')
        bank_statement_id = self.statement_import_model.create(cr, uid, dict(
                            file_type='qif',
                            data_file=qif_file,
                            ))
        self.statement_import_model.parse_file(cr, uid, [bank_statement_id])
        line_id = self.bank_statement_line_model.search(cr, uid, [('name', '=', 'YOUR LOCAL SUPERMARKET')])[0]
        statement_id = self.bank_statement_line_model.browse(cr, uid, line_id).statement_id.id
        bank_st_record = self.bank_statement_model.browse(cr, uid, statement_id)
        assert float_compare(bank_st_record.balance_end_real, -1896.09, 2) == 0
