from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource

class TestOfxFile(TransactionCase):
    """Tests for import bank statement ofx file format (account.bank.statement.import)
    """

    def setUp(self):
        super(TestOfxFile, self).setUp()
        self.statement_import_model = self.registry('account.bank.statement.import')
        self.bank_statement_model = self.registry('account.bank.statement')

    def test_ofx_file_import(self):
        try:
            from ofxparse import OfxParser as ofxparser
        except ImportError:
            #the Python library isn't installed on the server, the OFX import is unavailable and the test cannot be run
            return True
        cr, uid = self.cr, self.uid
        ofx_file_path = get_module_resource('account_bank_statement_import_ofx', 'test_ofx_file', 'test_ofx.ofx')
        ofx_file = open(ofx_file_path, 'rb').read().encode('base64')
        bank_statement_id = self.statement_import_model.create(cr, uid, dict(
                            file_type='ofx',
                            data_file=ofx_file,
                            ))
        self.statement_import_model.parse_file(cr, uid, [bank_statement_id])
        statement_id = self.bank_statement_model.search(cr, uid, [('name', '=', '000000123')])[0]
        bank_st_record = self.bank_statement_model.browse(cr, uid, statement_id)
        self.assertEquals(bank_st_record.balance_start, 2156.56)
        self.assertEquals(bank_st_record.balance_end_real, 1796.56)
