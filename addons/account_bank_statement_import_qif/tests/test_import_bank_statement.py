from openerp.tests.common import TransactionCase

qif_file = """IVR5cGU6QmFuawpEOC8xMi8xNApULTEsMDAwLjAwClBGcmFua3MgUGx1bWJpbmcKXgpEOC8xNS8xNApULTc1L
              jQ2ClBXYWx0cyBEcnVncwpeCkQzLzMvMTQKVC0zNzkuMDAKUENJVFkgT0YgU1BSSU5HRklFTEQKXgpEMy80LzE0ClQtMjAuM
              jgKUFlPVVIgTE9DQUwgU1VQRVJNQVJLRVQKXgpEMy8zLzE0ClQtNDIxLjM1ClBTUFJJTkdGSUVMRCBXQVRFUiBVVElMSVRZCl4K"""

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
        bank_temp_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'account', 'conf_bnk')
        self.bank_temp_id = bank_temp_ref and bank_temp_ref[1] or False
        bank_statement_id = self.statement_import_model.create(cr, uid, dict(
                            file_type = 'qif',
                            data_file = qif_file,
                            account_id = self.bank_temp_id
                             ))
        self.statement_import_model.parse_file(cr, uid, [bank_statement_id])
        line_id = self.bank_statement_line_model.search(cr, uid, [('name', '=', 'YOUR LOCAL SUPERMARKET')])[0]
        statement_id = self.bank_statement_line_model.browse(cr, uid, line_id).statement_id.id
        bank_st_record = self.bank_statement_model.browse(cr, uid, statement_id)
        assert float_compare(bank_st_record.balance_end_real, -1896.09, 2) == 0

