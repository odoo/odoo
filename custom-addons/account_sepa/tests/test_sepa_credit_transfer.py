# -*- coding: utf-8 -*-

import base64
from lxml import etree

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_sepa import sanitize_communication
from odoo.tests import tagged
from odoo.tools.misc import file_path


@tagged('post_install', '-at_install')
class TestSEPACreditTransfer(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.ref('base.EUR').active = True

        # tests doesn't go through the sanitization (_ is invalid)
        cls.partner_a.name = sanitize_communication(cls.partner_a.name)
        cls.partner_b.name = sanitize_communication(cls.partner_b.name)

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })

        # Create an IBAN bank account and its journal
        cls.bank_ing = cls.env['res.bank'].create({
            'name': 'ING',
            'bic': 'BBRUBEBB',
        })
        cls.bank_bnp = cls.env['res.bank'].create({
            'name': 'BNP Paribas',
            'bic': 'GEBABEBB',
        })

        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.bank_journal.write({
            'bank_id': cls.bank_ing.id,
            'bank_acc_number': 'BE48363523682327',
            'currency_id': cls.env.ref('base.EUR').id,
        })
        cls.sepa_ct = cls.bank_journal.outbound_payment_method_line_ids.filtered(lambda l: l.code == 'sepa_ct')
        cls.sepa_ct_method = cls.env.ref('account_sepa.account_payment_method_sepa_ct')

        # Make sure all suppliers have exactly one bank account
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.partner_a.id,
            'acc_number': 'BE08429863697813',
            'allow_out_payment': True,
            'bank_id': cls.bank_bnp.id,
            'currency_id': cls.env.ref('base.USD').id,
        })
        cls.env['res.partner.bank'].create({
            'acc_type': 'bank',
            'partner_id': cls.partner_b.id,
            'acc_number': '1234567890',
            'allow_out_payment': True,
            'bank_name': 'Mock & Co',
        })

        # Get a pain.001.001.03 schema validator
        schema_file_path = file_path('account_sepa/schemas/pain.001.001.03.xsd')
        cls.xmlschema = etree.XMLSchema(etree.parse(schema_file_path))

    @classmethod
    def createPayment(cls, partner, amount, ref=None):
        """ Create a SEPA credit transfer payment """
        return cls.env['account.payment'].create({
            'journal_id': cls.company_data['default_journal_bank'].id,
            'payment_method_line_id': cls.sepa_ct.id,
            'payment_type': 'outbound',
            'date': '2015-04-28',
            'amount': amount,
            'partner_id': partner.id,
            'partner_type': 'supplier',
            'ref': ref,
        })

    def testStandardSEPA(self):
        for bic in ["BBRUBEBB", False]:
            payment_1 = self.createPayment(self.partner_a, 500)
            payment_1.action_post()
            payment_2 = self.createPayment(self.partner_a, 600)
            payment_2.action_post()

            self.bank_journal.bank_id.bic = bic
            batch = self.env['account.batch.payment'].create({
                'journal_id': self.bank_journal.id,
                'payment_ids': [(4, payment.id, None) for payment in (payment_1 | payment_2)],
                'payment_method_id': self.sepa_ct_method.id,
                'batch_type': 'outbound',
            })

            self.assertFalse(batch.sct_generic)

            wizard_action = batch.validate_batch()
            self.assertFalse(wizard_action, "Validation wizard should not have returned an action")

            sct_doc = etree.fromstring(base64.b64decode(batch.export_file))
            self.assertTrue(self.xmlschema.validate(sct_doc), self.xmlschema.error_log.last_error)
            self.assertTrue(payment_1.is_move_sent)
            self.assertTrue(payment_2.is_move_sent)

    def testGenericSEPA(self):
        for bic in ["BBRUBEBB", False]:
            payment_1 = self.createPayment(self.partner_b, 500)
            payment_1.action_post()
            payment_2 = self.createPayment(self.partner_b, 700)
            payment_2.action_post()

            self.bank_journal.bank_id.bic = bic
            batch = self.env['account.batch.payment'].create({
                'journal_id': self.bank_journal.id,
                'payment_ids': [(4, payment.id, None) for payment in (payment_1 | payment_2)],
                'payment_method_id': self.sepa_ct_method.id,
                'batch_type': 'outbound',
            })

            self.assertTrue(batch.sct_generic)

            wizard_action = batch.validate_batch()
            self.assertTrue(wizard_action, "Validation wizard should have returned an action")
            self.assertEqual(wizard_action.get('res_model'), 'account.batch.error.wizard', "The action returned at validation should target an error wizard")

            error_wizard = self.env['account.batch.error.wizard'].browse(wizard_action['res_id'])
            self.assertTrue(len(error_wizard.warning_line_ids) > 0, "Using generic SEPA should raise warnings")
            self.assertTrue(len(error_wizard.error_line_ids) == 0, "Error wizard should not list any error")

            batch._send_after_validation()
            sct_doc = etree.fromstring(base64.b64decode(batch.export_file))
            self.assertTrue(self.xmlschema.validate(sct_doc), self.xmlschema.error_log.last_error)
            self.assertTrue(payment_1.is_move_sent)
            self.assertTrue(payment_2.is_move_sent)

    def testSEPAPainVersion(self):
        # Test to make sure the initial version is 'Generic' since it is a belgian IBAN
        self.assertEqual(self.bank_journal.sepa_pain_version, 'pain.001.001.03')

        # Change IBAN prefix to Germany and check that the pain version is updated accordingly
        self.bank_journal.bank_acc_number = 'DE48363523682327'
        self.assertEqual(self.bank_journal.sepa_pain_version, 'pain.001.001.03.de')

        # Provide an invalid IBAN to see if the pain version falls back to the company's fiscal country
        self.bank_journal.bank_acc_number = 'DEL48363523682327'
        self.env.company.account_fiscal_country_id = self.env.company.country_id = self.env.ref('base.ch')
        self.assertEqual(self.bank_journal.sepa_pain_version, 'pain.001.001.03.ch.02')

        # Remove the company's fiscal country and verify that the pain version now corresponds to the company's country
        self.env.company.country_id = self.env.company.country_id = self.env.ref('base.se')
        self.env.company.account_fiscal_country_id = None
        self.assertEqual(self.bank_journal.sepa_pain_version, 'pain.001.001.03.se')

    def test_sepa_character_conversion(self):
        """
        - Change the partner's name and street to contain non-latin characters
        - Check that communication (InstrId) is converted and trimmed to the correct unescaped size (max size = 35 characters)
        """
        self.partner_a.name = "ÀÎÑϐН"
        self.partner_a.bank_ids.acc_holder_name = "ÀÎÑϐН"
        self.partner_a.street = "íċēķθН"
        self.partner_a.city = "City"
        self.partner_a.country_id = self.env.ref('base.be')

        payment_1 = self.createPayment(self.partner_a, 500)
        payment_1.ref = "Wynand & Olivier are great fun!"
        payment_1.action_post()
        payment_2 = self.createPayment(self.partner_a, 700)
        payment_2.action_post()

        self.bank_journal.bank_id.bic = "BBRUBEBB"
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.bank_journal.id,
            'payment_ids': [(4, payment.id, None) for payment in (payment_1 | payment_2)],
            'payment_method_id': self.sepa_ct_method.id,
            'batch_type': 'outbound',
        })

        self.assertFalse(batch.sct_generic)

        wizard_action = batch.validate_batch()
        self.assertFalse(wizard_action, "Validation wizard should not have returned an action")

        ct_doc = etree.fromstring(base64.b64decode(batch.export_file))
        namespaces = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03'}
        name = ct_doc.findtext('.//ns:Cdtr/ns:Nm', namespaces=namespaces)
        street = ct_doc.findtext('.//ns:Cdtr/ns:PstlAdr/ns:AdrLine', namespaces=namespaces)
        InstrId = ct_doc.findtext('.//ns:InstrId', namespaces=namespaces)
        self.assertEqual(name, "AIN.N")
        self.assertEqual(street, "icekthN")
        self.assertEqual(len(InstrId), 31, "InstrId should be trimmed to 31 characters: `35 - len('amp;')`")

    def _check_structured_reference(self, country_code, payment):
        if country_code == 'ch':
            payment.partner_bank_id.sanitized_acc_number = 'CH4731000133285251000'
        payment.action_post()
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.bank_journal.id,
            'payment_ids': [(4, payment.id, None)],
            'payment_method_id': self.sepa_ct_method.id,
            'batch_type': 'outbound',
        })
        batch.validate_batch()

        ct_doc = etree.fromstring(base64.b64decode(batch.export_file))
        namespaces = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03'}
        strd_cd = ct_doc.findtext('.//ns:Strd/ns:CdtrRefInf/ns:Tp/ns:CdOrPrtry/ns:Cd', namespaces=namespaces)
        strd_prtry = ct_doc.findtext('.//ns:Strd/ns:CdtrRefInf/ns:Tp/ns:CdOrPrtry/ns:Prtry', namespaces=namespaces)
        strd_issr = ct_doc.findtext('.//ns:Strd/ns:CdtrRefInf/ns:Tp/ns:Issr', namespaces=namespaces)
        strd_ref = ct_doc.findtext('.//ns:Strd/ns:CdtrRefInf/ns:Ref', namespaces=namespaces)

        if country_code == 'ch':
            self.assertEqual(strd_prtry, 'QRR')
        else:
            self.assertEqual(strd_cd, 'SCOR')

        if country_code == 'be':
            self.assertEqual(strd_issr, 'BBA')
        elif country_code == 'eu':
            self.assertEqual(strd_issr, 'ISO')

        self.assertEqual(strd_ref, payment.ref)

    def test_structured_reference_eu(self):
        payment = self.createPayment(self.partner_a, 500, 'RF18539007547034')
        self._check_structured_reference('eu', payment)

    def test_structured_reference_be(self):
        self.partner_a.country_id = self.env.ref('base.be')
        payment = self.createPayment(self.partner_a, 500, '020343057642')
        self._check_structured_reference('be', payment)

    def test_structured_reference_ch(self):
        self.partner_a.country_id = self.env.ref('base.ch')
        payment = self.createPayment(self.partner_a, 500, '000000000000000000000012371')
        self._check_structured_reference('ch', payment)

    def test_structured_reference_fi(self):
        self.partner_a.country_id = self.env.ref('base.fi')
        payment = self.createPayment(self.partner_a, 500, '2023000098')
        self._check_structured_reference('fi', payment)

    def test_structured_reference_no(self):
        self.partner_a.country_id = self.env.ref('base.no')
        payment = self.createPayment(self.partner_a, 500, '1234567897')
        self._check_structured_reference('no', payment)
