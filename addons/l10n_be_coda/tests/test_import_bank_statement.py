from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource

class TestCodaFile(TransactionCase):
    """Tests for import bank statement coda file format (account.bank.statement.import)
    """

    def setUp(self):
        super(TestCodaFile, self).setUp()
        cr, uid = self.cr, self.uid
        self.statement_import_model = self.registry('account.bank.statement.import')
        self.bank_statement_model = self.registry('account.bank.statement')
        coda_file_path = get_module_resource('l10n_be_coda', 'test_coda_file', 'Ontvangen_CODA.2013-01-11-18.59.15.txt')
        self.coda_file = open(coda_file_path, 'rb').read().encode('base64')
        self.bank_statement_id = self.statement_import_model.create(cr, uid, dict(
                        data_file = self.coda_file,
                        journal_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'account', 'bank_journal').id,
        ))

    def test_coda_file_import(self):
        cr, uid = self.cr, self.uid
        self.statement_import_model.parse_file(cr, uid, [self.bank_statement_id])
        statement_id = self.bank_statement_model.search(cr, uid, [('name', '=', '135')])[0]
        bank_st_record = self.bank_statement_model.browse(cr, uid, statement_id)
        self.assertEquals(bank_st_record.balance_start, 11812.70)
        self.assertEquals(bank_st_record.balance_end_real, 13646.05)

    def test_coda_file_import_twice(self):
        cr, uid = self.cr, self.uid
        self.statement_import_model.parse_file(cr, uid, [self.bank_statement_id])
        with self.assertRaises(Exception):
            self.statement_import_model.parse_file(cr, uid, [self.bank_statement_id])

    def test_coda_file_wrong_journal(self):
        """ The demo account used by the CODA file is linked to the demo bank_journal """
        cr, uid = self.cr, self.uid
        bank_statement_id = self.statement_import_model.create(cr, uid, dict(
                        data_file = self.coda_file,
                        journal_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'account', 'check_journal').id
        ))
        with self.assertRaises(Exception):
            self.statement_import_model.parse_file(cr, uid, [bank_statement_id])
