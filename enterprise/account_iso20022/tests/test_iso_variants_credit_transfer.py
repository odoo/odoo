from lxml import etree
from odoo.addons.account_iso20022.tests.test_iso20022_common import TestISO20022CommonCreditTransfer
from odoo.tests import tagged
from odoo.tools.misc import file_path
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestGermanSEPACreditTransfer(TestISO20022CommonCreditTransfer):

    @classmethod
    def collect_company_accounting_data(cls, company):
        res = super().collect_company_accounting_data(company)
        cls.german_bank = cls.env['res.bank'].create({
            'name': 'Deutsche Bank',
            'bic': 'DEUTBEBE',
        })
        company.update({
            'vat': 'DE462612124',
            'currency_id': cls.env.ref('base.EUR').id,
            'country_id': cls.env.ref('base.de').id,
            'iso20022_orgid_id': '0123456789',
        })
        res['default_journal_bank'].update({
            'bank_acc_number': 'DE25500105173674149934',
            'bank_id': cls.german_bank.id
        })
        return res

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')
        cls.payment_method = cls.env.ref('account_iso20022.account_payment_method_sepa_ct')
        cls.company_data['default_journal_bank'].available_payment_method_ids |= cls.payment_method
        cls.payment_method_line = cls.env['account.payment.method.line'].sudo().create([{
            'name': cls.payment_method.name,
            'payment_method_id': cls.payment_method.id,
            'journal_id': cls.company_data['default_journal_bank'].id
        }])

        cls.env.ref('base.EUR').active = True
        cls.german_partner = cls.env['res.partner'].create({
            'name': 'German Customer',
            'street': 'German Street',
            'country_id': cls.env.ref('base.de').id,
        })
        cls.german_partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'DE24500105171688544432',
            'partner_id': cls.german_partner.id,
            'acc_type': 'bank',
            'bank_name': 'Deutsche Bank',
            'bank_id': cls.german_bank.id,
            'allow_out_payment': True,
        })

    @freeze_time('2024-03-04')
    def test_german_sct_xml(self):
        batch = self.generate_iso20022_batch_payment(self.german_partner)
        sct_doc = self.get_sct_doc_from_batch(batch)
        xml_file_path = file_path('account_iso20022/tests/xml_files/pain.001.001.03.de.xml')
        expected_tree = etree.parse(xml_file_path)

        self.assertXmlTreeEqual(sct_doc, expected_tree.getroot())


@tagged('post_install', '-at_install')
class TestAustrianSEPACreditTransfer(TestISO20022CommonCreditTransfer):

    @classmethod
    def collect_company_accounting_data(cls, company):
        res = super().collect_company_accounting_data(company)
        company.update({
            'vat': 'ATU12345675',
            'currency_id': cls.env.ref('base.EUR').id,
            'country_id': cls.env.ref('base.at').id,
            'iso20022_orgid_id': '0123456789',
        })
        cls.austrian_bank = cls.env['res.bank'].create({
            'name': 'UNICREDIT BANK AUSTRIA AG',
            'bic': 'BKAUATWWXXX',
        })
        res['default_journal_bank'].update({
            'bank_acc_number': 'AT61 5400 0825 4928 3818',
            'bank_id': cls.austrian_bank.id
        })
        return res

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')
        cls.env.ref('base.EUR').active = True
        cls.payment_method = cls.env.ref('account_iso20022.account_payment_method_sepa_ct')
        cls.company_data['default_journal_bank'].available_payment_method_ids |= cls.payment_method
        cls.payment_method_line = cls.env['account.payment.method.line'].sudo().create([{
            'name': cls.payment_method.name,
            'payment_method_id': cls.payment_method.id,
            'journal_id': cls.company_data['default_journal_bank'].id
        }])
        cls.austrian_partner = cls.env['res.partner'].create({
            'name': 'Austrian Customer',
            'street': 'Austrian Street',
            'country_id': cls.env.ref('base.at').id,
        })
        cls.austrian_partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'AT35 2060 4961 4719 6834',
            'allow_out_payment': True,
            'partner_id': cls.austrian_partner.id,
            'acc_type': 'bank',
            'bank_name': 'UNICREDIT BANK AUSTRIA AG',
            'bank_id': cls.austrian_bank.id,
        })

    @freeze_time('2024-03-04')
    def test_austrian_sct_xml(self):
        batch = self.generate_iso20022_batch_payment(self.austrian_partner)
        sct_doc = self.get_sct_doc_from_batch(batch)
        xml_file_path = file_path('account_iso20022/tests/xml_files/pain.001.001.03.austrian.004.xml')
        expected_tree = etree.parse(xml_file_path)
        self.assertXmlTreeEqual(sct_doc, expected_tree.getroot())


@tagged('post_install', '-at_install')
class TestSwedishIsoCreditTransfer(TestISO20022CommonCreditTransfer):

    @classmethod
    def collect_company_accounting_data(cls, company):
        res = super().collect_company_accounting_data(company)
        cls.swedish_bank = cls.env['res.bank'].create({
            'name': 'SwedBank',
            'bic': 'SWEDSESSXXX',
        })
        # the Swedish pain version should be able to handle empty address fields
        company.update({
            'vat': 'SE123456789701',
            'currency_id': cls.env.ref('base.SEK').id,
            'country_id': cls.env.ref('base.se').id,
            'street': '',
            'city': '',
            'zip': '',
            'iso20022_orgid_id': '0123456789',
        })
        res['default_journal_bank'].update({
            'bank_acc_number': 'SE7335536296831513338982',
            'bank_id': cls.swedish_bank.id,
        })
        return res

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')
        cls.env.ref('base.SEK').active = True
        cls.payment_method = cls.env.ref('account_iso20022.account_payment_method_iso20022_se')
        cls.company_data['default_journal_bank'].available_payment_method_ids |= cls.payment_method
        cls.payment_method_line = cls.env['account.payment.method.line'].sudo().create([{
            'name': cls.payment_method.name,
            'payment_method_id': cls.payment_method.id,
            'journal_id': cls.company_data['default_journal_bank'].id
        }])

        cls.swedish_partner = cls.env['res.partner'].create({
            'name': 'Swedish Partner',
            'street': 'Swedish Street',
            'country_id': cls.env.ref('base.se').id,
        })
        cls.swedish_partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'SE4550000000058398257466',
            'allow_out_payment': True,
            'partner_id': cls.swedish_partner.id,
            'acc_type': 'bank',
            'bank_name': 'Swedbank',
        })
        cls.swedish_iso_pay_method = cls.company_data['default_journal_bank'].outbound_payment_method_line_ids.filtered(
            lambda l: l.code == 'iso20022_se')
        cls.swedish_iso_pay_method = cls.env.ref('account_iso20022.account_payment_method_iso20022_se')

    @freeze_time('2024-03-04')
    def test_swedish_iso_xml(self):
        batch = self.generate_iso20022_batch_payment(self.swedish_partner)
        sct_doc = self.get_sct_doc_from_batch(batch)
        xml_file_path = file_path('account_iso20022/tests/xml_files/pain.001.001.09.se.xml')
        expected_tree = etree.parse(xml_file_path)

        self.assertXmlTreeEqual(sct_doc, expected_tree.getroot())


@tagged('post_install', '-at_install')
class TestSwissIsoCreditTransfer(TestISO20022CommonCreditTransfer):

    @classmethod
    def collect_company_accounting_data(cls, company):
        res = super().collect_company_accounting_data(company)
        cls.swiss_bank = cls.env['res.bank'].create({
            'name': 'ONE SWISS BANK SA',
            'bic': 'BQBHCHGG',
        })
        company.update({
            'country_id': cls.env.ref('base.ch').id,
            'vat': 'CHE-530781296TVA',
            'currency_id': cls.env.ref('base.CHF').id,
            'iso20022_orgid_id': '0123456789'
        })
        res['default_journal_bank'].update({
            'bank_acc_number': 'CH4431999123000889012',
            'bank_id': cls.swiss_bank.id
        })
        return res

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')
        cls.env.ref('base.CHF').active = True

        cls.payment_method = cls.env.ref('account_iso20022.account_payment_method_iso20022_ch')
        cls.company_data['default_journal_bank'].available_payment_method_ids |= cls.payment_method
        cls.payment_method_line = cls.env['account.payment.method.line'].sudo().create([{
            'name': cls.payment_method.name,
            'payment_method_id': cls.payment_method.id,
            'journal_id': cls.company_data['default_journal_bank'].id
        }])

        cls.swiss_partner = cls.env['res.partner'].create({
            'name': 'Easy Clean Lausanne',
            'street': 'Rte de Prilly 18, 1004 Lausanne, Suisse',
            'zip': 1004,
            'city': 'Lausanne',
            'country_id': cls.env.ref('base.ch').id,
        })
        cls.swiss_partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'CH11 3000 5228 1308 3501 F',
            'allow_out_payment': True,
            'partner_id': cls.swiss_partner.id,
            'acc_type': 'bank',
            'bank_name': 'swiss_bank'
        })

    @freeze_time('2024-03-04')
    def test_swiss_iso_xml_pain_03(self):
        self.company_data['default_journal_bank'].sepa_pain_version = 'pain.001.001.03'
        batch = self.generate_iso20022_batch_payment(self.swiss_partner)
        sct_doc = self.get_sct_doc_from_batch(batch)
        xml_file_path = file_path('account_iso20022/tests/xml_files/pain.001.001.03.ch.02.xml')
        expected_tree = etree.parse(xml_file_path)
        self.assertXmlTreeEqual(sct_doc, expected_tree.getroot())

    @freeze_time('2024-03-04')
    def test_swiss_iso_xml_pain_09(self):
        batch = self.generate_iso20022_batch_payment(self.swiss_partner, memo="210000000003139471430009017")
        sct_doc = self.get_sct_doc_from_batch(batch)
        xml_file_path = file_path('account_iso20022/tests/xml_files/pain.001.001.09.ch.03.xml')
        expected_tree = etree.parse(xml_file_path)
        self.assertXmlTreeEqual(sct_doc, expected_tree.getroot())
