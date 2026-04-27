from lxml import etree
from odoo.addons.account_iso20022.tests.test_iso_variants_credit_transfer import TestSwedishIsoCreditTransfer
from odoo.tests import tagged
from odoo.tools.misc import file_path
from freezegun import freeze_time


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestSwedishIsoBBANCreditTransfer(TestSwedishIsoCreditTransfer):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.swedish_partner_bank.bank_id = cls.swedish_bank

    @freeze_time('2024-03-04')
    def test_bankgiro(self):
        self.company_data['default_journal_bank'].bank_account_id.allow_out_payment = False
        self.company_data['default_journal_bank'].bank_acc_number = '6543-2106'
        self.swedish_partner_bank.lock_trust_fields = False
        self.swedish_partner_bank.acc_number = '1234-5617'
        self.assertEqual(self.swedish_partner_bank.acc_type, 'bankgiro')
        batch = self.generate_iso20022_batch_payment(self.swedish_partner, '78949')
        sct_doc = self.get_sct_doc_from_batch(batch)
        xml_file_path = file_path('l10n_se_bban/tests/data/bankgiro.xml')
        expected_tree = etree.parse(xml_file_path)

        self.assertXmlTreeEqual(sct_doc, expected_tree.getroot())

    @freeze_time('2024-03-04')
    def test_plusgiro(self):
        self.company_data['default_journal_bank'].bank_account_id.allow_out_payment = False
        self.company_data['default_journal_bank'].bank_acc_number = '654321-9'
        self.swedish_partner_bank.lock_trust_fields = False
        self.swedish_partner_bank.acc_number = '543210-9'
        self.assertEqual(self.swedish_partner_bank.acc_type, 'plusgiro')
        batch = self.generate_iso20022_batch_payment(self.swedish_partner)
        sct_doc = self.get_sct_doc_from_batch(batch)
        xml_file_path = file_path('l10n_se_bban/tests/data/plusgiro.xml')
        expected_tree = etree.parse(xml_file_path)

        self.assertXmlTreeEqual(sct_doc, expected_tree.getroot())

    @freeze_time('2024-03-04')
    def test_bban(self):
        self.company_data['default_journal_bank'].bank_account_id.allow_out_payment = False
        self.company_data['default_journal_bank'].bank_acc_number = '12200108451'
        self.assertEqual(self.company_data['default_journal_bank'].bank_account_id.acc_type, 'bban_se')
        self.swedish_partner_bank.lock_trust_fields = False
        self.swedish_partner_bank.acc_number = '96602675631'
        self.assertEqual(self.swedish_partner_bank.acc_type, 'bban_se')
        batch = self.generate_iso20022_batch_payment(self.swedish_partner)
        sct_doc = self.get_sct_doc_from_batch(batch)
        xml_file_path = file_path('l10n_se_bban/tests/data/bban.xml')
        expected_tree = etree.parse(xml_file_path)

        self.assertXmlTreeEqual(sct_doc, expected_tree.getroot())

    @freeze_time('2024-03-04')
    def test_batch_payment_with_iban_and_bban(self):
        bban_partner = self.env['res.partner'].create({
            'name': 'Swedish Partner',
            'street': 'Swedish Street',
            'country_id': self.env.ref('base.se').id,
        })
        self.env['res.partner.bank'].create({
            'acc_number': '96602675631',
            'allow_out_payment': True,
            'partner_id': bban_partner.id,
            'bank_name': 'Swedbank',
        })
        payments = self.env['account.payment'].create([{
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.payment_method_line.id,
            'payment_type': 'outbound',
            'date': '2024-03-04',
            'amount': 500,
            'partner_id': self.swedish_partner.id,
            'partner_type': 'supplier',
            'memo': '123',
        }, {
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.payment_method_line.id,
            'payment_type': 'outbound',
            'date': '2024-03-04',
            'amount': 500,
            'partner_id': bban_partner.id,
            'partner_type': 'supplier',
            'memo': '456',
        }])
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': payments.ids,
            'payment_method_id': self.payment_method.id,
            'batch_type': 'outbound',
            'iso20022_batch_booking': True,
        })
        batch.validate_batch()
        batch_attachment = self.env['ir.attachment'].search_count([
            ('res_model', '=', 'account.batch.payment'),
            ('res_id', '=', batch.id),
            ('mimetype', '=', 'application/zip'),
        ])
        self.assertEqual(batch_attachment, 1)

    @freeze_time('2024-03-04')
    def test_batch_payment_with_different_banks(self):
        nordea, swedbank = self.env['res.bank'].create([{
            'name': 'Nordea',
            'bic': 'NDEASESS',
        }, {
            'name': 'Swedbank',
            'bic': 'SWEDSESS',
        }])
        nordea_partner, swedbank_partner = self.env['res.partner'].create([{
            'name': 'Nordea Customer',
            'country_id': self.env.ref('base.se').id,
        }, {
            'name': 'Swedbank Customer',
            'country_id': self.env.ref('base.se').id,
        }])
        self.env['res.partner.bank'].create([{
            'acc_number': '654321-9',
            'allow_out_payment': True,
            'partner_id': nordea_partner.id,
            'bank_id': nordea.id,
        }, {
            'acc_number': '96602675632',
            'allow_out_payment': True,
            'partner_id': swedbank_partner.id,
            'bank_id': swedbank.id,
        }])
        nordea_journal, swedbank_journal = self.env['account.journal'].create([{
            'name': 'Nordea Journal',
            'code': 'BK-NORD',
            'type': 'bank',
            'sepa_pain_version': 'pain.001.001.03',
            'bank_account_id': self.company_data['default_journal_bank'].bank_account_id.id,
        }, {
            'name': 'Swedbank Journal',
            'code': 'BK-SWED',
            'type': 'bank',
            'sepa_pain_version': 'pain.001.001.03',
            'bank_account_id': self.company_data['default_journal_bank'].bank_account_id.id,
        }])
        nordea_payment, swedbank_payment = self.env['account.payment'].create([{
            'journal_id': nordea_journal.id,
            'payment_method_line_id': nordea_journal.outbound_payment_method_line_ids.filtered(lambda pml: pml.code == 'iso20022_se').id,
            'payment_type': 'outbound',
            'date': '2024-03-04',
            'amount': 500,
            'partner_id': nordea_partner.id,
            'partner_type': 'supplier',
            'memo': '123',
        }, {
            'journal_id': swedbank_journal.id,
            'payment_method_line_id': swedbank_journal.outbound_payment_method_line_ids.filtered(lambda pml: pml.code == 'iso20022_se').id,
            'payment_type': 'outbound',
            'date': '2024-03-04',
            'amount': 500,
            'partner_id': swedbank_partner.id,
            'partner_type': 'supplier',
            'memo': '456',
        }])
        nordea_batch, swedbank_batch = self.env['account.batch.payment'].create([{
            'journal_id': nordea_journal.id,
            'payment_ids': nordea_payment.ids,
            'payment_method_id': self.payment_method.id,
            'batch_type': 'outbound',
        }, {
            'journal_id': swedbank_journal.id,
            'payment_ids': swedbank_payment.ids,
            'payment_method_id': self.payment_method.id,
            'batch_type': 'outbound',
        }])
        nordea_batch.validate_batch()
        swedbank_batch.validate_batch()
        nordea_xml_file = self.get_sct_doc_from_batch(nordea_batch)
        swedbank_xml_file = self.get_sct_doc_from_batch(swedbank_batch)
        nordea_xml_file_path = file_path('l10n_se_bban/tests/data/test_batch_nordea.xml')
        swedbank_xml_file_path = file_path('l10n_se_bban/tests/data/test_batch_swedbank.xml')

        self.assertXmlTreeEqual(nordea_xml_file, etree.parse(nordea_xml_file_path).getroot())
        self.assertXmlTreeEqual(swedbank_xml_file, etree.parse(swedbank_xml_file_path).getroot())

    def test_10n_se_account_types_computation(self):
        self.swedish_partner_bank.lock_trust_fields = False
        self.swedish_partner_bank.acc_number = '1-8'
        self.assertEqual(self.swedish_partner_bank.acc_type, 'plusgiro')
        self.swedish_partner_bank.acc_number = '112-3'
        self.assertEqual(self.swedish_partner_bank.acc_type, 'plusgiro')
        self.swedish_partner_bank.acc_number = '38201-0'
        self.assertEqual(self.swedish_partner_bank.acc_type, 'plusgiro')
        self.swedish_partner_bank.acc_number = '678653833066'
        self.assertEqual(self.swedish_partner_bank.acc_type, 'bban_se')
        self.swedish_partner_bank.acc_number = '99603406872188'
        self.assertEqual(self.swedish_partner_bank.acc_type, 'bban_se')
