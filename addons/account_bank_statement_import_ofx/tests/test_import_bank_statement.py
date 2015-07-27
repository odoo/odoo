from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestOfxFile(TransactionCase):
    """ Tests for import bank statement ofx file format (account.bank.statement.import) """

    def test_ofx_file_import(self):
        try:
            from ofxparse import OfxParser as ofxparser
        except ImportError:
            #the Python library isn't installed on the server, the OFX import is unavailable and the test cannot be run
            return True
        
        # Get OFX file content
        ofx_file_path = get_module_resource('account_bank_statement_import_ofx', 'test_ofx_file', 'test_ofx.ofx')
        ofx_file = open(ofx_file_path, 'rb').read().encode('base64')

        # Create a bank account and journal corresponding to the OFX file (same currency and account number)
        bank_account_id = self.env['res.partner.bank'].create({'acc_number': '123456', 'bank_name': 'a', 'state': 'bank', 'partner_id': self.env.ref('base.main_partner').id}).id
        bank_journal_id = self.env['account.journal'].create({'name': 'Bank 123456', 'code': 'BNK67', 'currency_id': self.env.ref("base.USD").id, 'type': 'bank', 'bank_account_id': bank_account_id}).id
        
        # Use an import wizard to process the file
        import_wizard = self.env['account.bank.statement.import'].with_context(journal_id=bank_journal_id).create({'data_file': ofx_file})
        import_wizard.import_file()

        # Check the imported bank statement
        bank_st_record = self.env['account.bank.statement'].search([('name', '=', '000000123')])[0]
        self.assertEqual(bank_st_record.balance_start, 2516.56)
        self.assertEqual(bank_st_record.balance_end_real, 2156.56)

        # Check an imported bank statement line
        line = bank_st_record.line_ids.filtered(lambda r: r.unique_import_id == '123456-219378')
        self.assertEqual(line.name, 'Agrolait')
        self.assertEqual(line.amount, -80)
        self.assertEqual(line.partner_id.id, self.ref('base.res_partner_2'))
        self.assertEqual(line.bank_account_id.id, self.ref('account_bank_statement_import.ofx_partner_bank_1'))
