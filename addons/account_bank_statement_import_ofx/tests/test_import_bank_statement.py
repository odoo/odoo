from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestOfxFile(TransactionCase):
    """Tests for import bank statement ofx file format (account.bank.statement.import)
    """

    def setUp(self):
        super(TestOfxFile, self).setUp()
        self.statement_import_model = self.env['account.bank.statement.import']
        self.bank_statement_model = self.env['account.bank.statement']

    def test_ofx_file_import(self):
        try:
            from ofxparse import OfxParser as ofxparser
        except ImportError:
            #the Python library isn't installed on the server, the OFX import is unavailable and the test cannot be run
            return True
        ofx_file_path = get_module_resource('account_bank_statement_import_ofx', 'test_ofx_file', 'test_ofx.ofx')
        ofx_file = open(ofx_file_path, 'rb').read().encode('base64')

        import_wizard = self.statement_import_model.create(dict(data_file=ofx_file))
        create_journal_wizard = self.env['account.bank.statement.import.journal.creation']\
            .with_context(statement_import_transient_id=import_wizard.id)\
            .create({'name': 'Bank 123456', 'currency_id': self.env.ref("base.USD").id, 'account_number': '123456'})
        create_journal_wizard.create_journal() # Note: also finishes import
        bank_st_record = self.bank_statement_model.search([('name', '=', '000000123')])[0]

        self.assertEqual(bank_st_record.balance_start, 2516.56)
        self.assertEqual(bank_st_record.balance_end_real, 2156.56)

        line = bank_st_record.line_ids[-1]
        self.assertEqual(line.name, 'Agrolait')
        self.assertEqual(line.ref, '219378')
        self.assertEqual(line.partner_id.id, self.ref('base.res_partner_2'))
        self.assertEqual(line.bank_account_id.id, self.ref('account_bank_statement_import.ofx_partner_bank_1'))