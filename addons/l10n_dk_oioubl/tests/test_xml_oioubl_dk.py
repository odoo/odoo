from freezegun import freeze_time

from odoo import Command
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLDK(TestUBLCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="dk"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.dk').id,
            'currency_id': cls.env.ref('base.DKK').id,
            'city': 'Aalborg',
            'zip': '9430',
            'vat': 'DK12345674',
            'phone': '+45 32 12 34 56',
            'street': 'Paradisæblevej, 10',
            'invoice_is_ubl_cii': True,
        })
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'DK5000400440116243',
        })

        cls.partner_a.write({
            'name': 'SUPER DANISH PARTNER',
            'city': 'Aalborg',
            'zip': '9430',
            'vat': 'DK12345674',
            'phone': '+45 32 12 35 56',
            'street': 'Paradisæblevej, 11',
            'country_id': cls.env.ref('base.dk').id,
            'ubl_cii_format': 'oioubl_201',
        })
        cls.partner_b.write({
            'name': 'SUPER BELGIAN PARTNER',
            'street': 'Rue du Paradis, 10',
            'zip': '6870',
            'city': 'Eghezee',
            'country_id': cls.env.ref('base.be').id,
            'phone': '061928374',
            'vat': 'BE0897223670',
            'ubl_cii_format': 'oioubl_201',
        })
        cls.partner_c = cls.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': cls.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'company_registry': '123 568 941 00056',
            'ubl_cii_format': 'oioubl_201',
        })
        cls.dk_local_tax_1 = cls.env["account.chart.template"].ref('tax120')
        cls.dk_local_tax_2 = cls.env["account.chart.template"].ref('tax110')
        cls.dk_foreign_tax_1 = cls.env["account.chart.template"].ref('tax210')
        cls.dk_foreign_tax_2 = cls.env["account.chart.template"].ref('tax220')

    def create_post_and_send_invoice(self, partner=None, move_type='out_invoice'):
        if not partner:
            partner = self.partner_a

        if partner == self.partner_a:
            # local dk taxes
            tax_1, tax_2 = self.dk_local_tax_1, self.dk_local_tax_2
        else:
            # dk taxes for foreigners
            tax_1, tax_2 = self.dk_foreign_tax_1, self.dk_foreign_tax_2

        invoice = self.env["account.move"].create({
            'move_type': move_type,
            'partner_id': partner.id,
            'partner_bank_id': self.env.company.partner_id.bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'narration': 'test narration',
            'ref': 'ref_move',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(tax_1.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_2.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice._generate_pdf_and_send_invoice(self.move_template, from_cron=False, allow_fallback_pdf=False)
        return invoice

    @freeze_time('2017-01-01')
    def test_export_invoice_two_line_partner_dk(self):
        invoice = self.create_post_and_send_invoice()
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_partner_dk.xml")

    @freeze_time('2017-01-01')
    def test_export_invoice_two_line_foreign_partner_be(self):
        invoice = self.create_post_and_send_invoice(partner=self.partner_b)
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_foreign_partner_be.xml")

    @freeze_time('2017-01-01')
    def test_export_invoice_two_line_foreign_partner_fr(self):
        invoice = self.create_post_and_send_invoice(partner=self.partner_c)
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_foreign_partner_fr.xml")

    @freeze_time('2017-01-01')
    def test_export_credit_note_two_line_partner_dk(self):
        refund = self.create_post_and_send_invoice(move_type='out_refund')
        self.assertTrue(refund.ubl_cii_xml_id)
        self._assert_invoice_attachment(refund.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_refund_partner_dk.xml")

    @freeze_time('2017-01-01')
    def test_export_credit_note_two_line_partner_fr(self):
        refund = self.create_post_and_send_invoice(partner=self.partner_c, move_type='out_refund')
        self.assertTrue(refund.ubl_cii_xml_id)
        self._assert_invoice_attachment(refund.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_refund_foreign_partner_fr.xml")

    @freeze_time('2017-01-01')
    def test_oioubl_export_should_still_be_valid_when_currency_has_more_precision_digit(self):
        self.company_data['company'].currency_id.rounding = 0.001
        invoice = self.create_post_and_send_invoice()
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_partner_dk.xml")

    @freeze_time('2017-01-01')
    def test_oioubl_export_should_raise_an_error_when_partner_building_number_is_missing(self):
        self.partner_a.street = 'Paradisæblevej'  # remove the street number from the address
        with self.assertRaisesRegex(UserError, "The following partner's street number is missing"):
            self.create_post_and_send_invoice()

    @freeze_time('2017-01-01')
    def test_oioubl_export_should_raise_an_error_when_company_building_number_is_missing(self):
        self.env.company.partner_id.street = 'Paradisæblevej'
        with self.assertRaisesRegex(UserError, "The following partner's street number is missing"):
            self.create_post_and_send_invoice()

    @freeze_time('2017-01-01')
    def test_export_invoice_company_and_partner_without_country_code_prefix_in_vat(self):
        self.company_data['company'].vat = '12345674'
        self.partner_a.vat = 'DK12345674'
        invoice = self.create_post_and_send_invoice()
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_partner_dk.xml")

    @freeze_time('2017-01-01')
    def test_export_partner_fr_without_siret_should_raise_an_error(self):
        self.partner_c.company_registry = False
        with self.assertRaisesRegex(UserError, "The company registry is required for french partner:"):
            self.create_post_and_send_invoice(partner=self.partner_c)
