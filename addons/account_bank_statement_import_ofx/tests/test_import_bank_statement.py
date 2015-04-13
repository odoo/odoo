from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestOfxFile(TransactionCase):
    """Tests for import bank statement ofx file format
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestOfxFile, self).setUp()
        self.statement_import_model = self.env['account.bank.statement.import']
        self.bank_statement_model = self.env['account.bank.statement']

    def test_ofx_file_import(self):
        try:
            from ofxparse import OfxParser as ofxparser
        except ImportError:
            # the Python library isn't installed on the server, the OFX import
            # is unavailable and the test cannot be run
            return True
        ofx_file_path = get_module_resource(
            'account_bank_statement_import_ofx',
            'test_ofx_file', 'test_ofx.ofx')
        ofx_file = open(ofx_file_path, 'rb').read().encode('base64')
        bank_statement = self.statement_import_model.create(
            dict(data_file=ofx_file))
        bank_statement.import_file()
        bank_st_record = self.bank_statement_model.search(
            [('name', '=', '000000123')])[0]
        self.assertEquals(bank_st_record.balance_start, 2156.56)
        self.assertEquals(bank_st_record.balance_end_real, 1796.56)

        line = bank_st_record.line_ids[0]
        self.assertEquals(line.name, 'Agrolait')
        self.assertEquals(line.ref, '219378')
        self.assertEquals(line.partner_id.id, self.ref('base.res_partner_2'))
        self.assertEquals(
            line.bank_account_id.id,
            self.ref('account_bank_statement_import.ofx_partner_bank_1'))
