# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from lxml import etree

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import test_xsd


class TestSEPACreditTransferUpdateCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
            'iso20022_lei': '04774727010477472701',
        })

        cls.env.ref('base.EUR').active = True

        cls.bank_ing = cls.env['res.bank'].create({
            'name': 'ING',
            'bic': 'BBRUBEBB',
        })

        cls.partner_a.write({
            'country_id': cls.env.ref('base.be'),
            'iso20022_lei': '05874837010477472802',
            'street': 'Test street',
            'zip': '12345',
            'city': 'testcity',
        })
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.partner_a.id,
            'acc_number': 'BE08429863697813',
            'bank_id': cls.bank_ing.id,
            'currency_id': cls.env.ref('base.EUR').id,
        })

        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.bank_journal.write({
            'bank_id': cls.bank_ing.id,
            'bank_acc_number': 'BE48363523682327',
            'currency_id': cls.env.ref('base.EUR').id,
        })
        cls.bank_journal.sepa_pain_version = 'pain.001.001.09'

        cls.sepa_ct = cls.env.ref('account_iso20022.account_payment_method_sepa_ct')

        cls.payment = cls.env['account.payment'].create({
            'journal_id': cls.bank_journal.id,
            'payment_type': 'outbound',
            'date': '2023-06-01',
            'amount': 500,
            'partner_id': cls.partner_a.id,
            'partner_type': 'supplier',
        })
        cls.payment.payment_method_id = cls.sepa_ct.id
        cls.payment.partner_bank_id.allow_out_payment = True
        cls.payment.action_post()

        cls.batch = cls.env['account.batch.payment'].create({
            'journal_id': cls.bank_journal.id,
            'payment_ids': [Command.set(cls.payment.ids)],
            'payment_method_id': cls.sepa_ct.id,
            'batch_type': 'outbound',
        })


@tagged('post_install', '-at_install', 'curr')
class TestSEPACreditTransferUpdate(TestSEPACreditTransferUpdateCommon):

    def test_new_generic_sepa_version_001_001_09(self):

        self.batch.validate_batch()
        self.assertTrue(self.payment.is_sent)
        sct_doc = etree.fromstring(b64decode(self.batch.export_file))

        namespaces = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.09'}
        execution_date = sct_doc.findtext('.//ns:PmtInf/ns:ReqdExctnDt/ns:Dt', namespaces=namespaces)
        cdtr_lei = sct_doc.findtext('.//ns:CdtTrfTxInf/ns:CdtrAgt/ns:FinInstnId/ns:LEI', namespaces=namespaces)
        dbtr_lei = sct_doc.findtext('.//ns:PmtInf/ns:Dbtr/ns:Id/ns:OrgId/ns:LEI', namespaces=namespaces)

        self.assertEqual(execution_date, self.batch.date.strftime('%Y-%m-%d'))
        self.assertEqual(cdtr_lei, self.partner_a.iso20022_lei)
        self.assertEqual(dbtr_lei, self.company_data['company'].iso20022_lei)

        partner_address = sct_doc.find('.//ns:CdtTrfTxInf/ns:Cdtr/ns:PstlAdr', namespaces=namespaces)
        street = partner_address.findtext('ns:StrtNm', namespaces=namespaces)
        postal_code = partner_address.findtext('ns:PstCd', namespaces=namespaces)
        city = partner_address.findtext('ns:TwnNm', namespaces=namespaces)
        adr_line = partner_address.findtext('ns:AdrLine', namespaces=namespaces)

        self.assertEqual(street, self.partner_a.street)
        self.assertEqual(postal_code, self.partner_a.zip)
        self.assertEqual(city, self.partner_a.city)
        self.assertFalse(adr_line)


@tagged('external_l10n', 'post_install', '-at_install', '-standard')
class TestSEPACreditTransferUpdateXmlValidity(TestSEPACreditTransferUpdateCommon):
    @test_xsd(path='account_sepa/schemas/pain.001.001.09.xsd')
    def test_xml_validity(self):
        return etree.fromstring(b64decode(self.batch.export_file))
