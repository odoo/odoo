from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestOfxFile(TransactionCase):
    """Tests for import bank statement ofx file format (account.bank.statement.import)
    """

    def setUp(self):
        super(TestOfxFile, self).setUp()
        self.BankStatementImport = self.env['account.bank.statement.import']
        self.BankStatement = self.env['account.bank.statement']

    def test_ofx_file_import(self):
        try:
            from ofxparse import OfxParser as ofxparser
        except ImportError:
            #the Python library isn't installed on the server, the OFX import is unavailable and the test cannot be run
            return True
        ofx_file_path = get_module_resource('account_bank_statement_import_ofx', 'test_ofx_file', 'test_ofx.ofx')
        ofx_file = open(ofx_file_path, 'rb').read().encode('base64')
        bank_statement_id = self.BankStatementImport.create(dict(
            data_file=ofx_file,
        ))
        bank_statement_id.import_file()
        statement = self.BankStatement.search([('name', '=', '000000123')], limit=1)
        self.assertEquals(statement.balance_start, 2516.56)
        self.assertEquals(statement.balance_end_real, 2156.56)
