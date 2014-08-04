from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource

class TestCodaFile(TransactionCase):
    """Tests for import bank statement coda file format (account.bank.statement.import)
    """

    def setUp(self):
        super(TestCodaFile, self).setUp()
        self.statement_import_model = self.registry('account.bank.statement.import')
        self.bank_statement_model = self.registry('account.bank.statement')

    def test_coda_file_import(self):
        cr, uid = self.cr, self.uid
        bank_temp_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'account', 'conf_bnk')
        partner_id_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'main_partner')
        company_id_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'main_company')
        self.bank_temp_id = bank_temp_ref and bank_temp_ref[1] or False
        self.partner_id = partner_id_ref and partner_id_ref[1] or False
        self.company_id = company_id_ref and company_id_ref[1] or False
        coda_file_path = get_module_resource('l10n_be_coda', 'test_coda_file', 'Ontvangen_CODA.2013-01-11-18.59.15.txt')
        coda_file = open(coda_file_path, 'rb').read().encode('base64')
        bank_account_id = self.registry('res.partner.bank').create(cr, uid, dict(
                        state = 'bank',
                        acc_number = 'BE33737018595246',
                        bank_name = 'Reserve',
                        partner_id = self.partner_id,
                        company_id = self.company_id
                        ))
        bank_statement_id = self.statement_import_model.create(cr, uid, dict(
                        file_type = 'coda',
                        data_file = coda_file,
                         ))
        self.statement_import_model.parse_file(cr, uid, [bank_statement_id])
        statement_id = self.bank_statement_model.search(cr, uid, [('name', '=', '135')])[0]
        bank_st_record = self.bank_statement_model.browse(cr, uid, statement_id)
        self.assertEquals(bank_st_record.balance_start, 11812.70)
        self.assertEquals(bank_st_record.balance_end_real, 13527.81)

