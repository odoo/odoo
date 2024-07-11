from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open


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
        cls.dk_local_sale_tax_1 = cls.env["account.chart.template"].ref('tax_s1y')
        cls.dk_local_sale_tax_2 = cls.env["account.chart.template"].ref('tax_s1')
        cls.dk_foreign_sale_tax_1 = cls.env["account.chart.template"].ref('tax_s0')
        cls.dk_foreign_sale_tax_2 = cls.env["account.chart.template"].ref('tax_s7')
        cls.dk_local_purchase_tax_goods = cls.env["account.chart.template"].ref('tax_k1')

    def create_post_and_send_invoice(self, partner=None, move_type='out_invoice'):
        if not partner:
            partner = self.partner_a

        if partner == self.partner_a:
            # local dk taxes
            tax_1, tax_2 = self.dk_local_sale_tax_1, self.dk_local_sale_tax_2
        else:
            # dk taxes for foreigners
            tax_1, tax_2 = self.dk_foreign_sale_tax_1, self.dk_foreign_sale_tax_2

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
        self.env['account.move.send'] \
            .with_context(active_model=invoice._name, active_ids=invoice.ids) \
            .create({}) \
            .action_send_and_print()
        return invoice

    #########
    # EXPORT
    #########

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
        self.partner_c.ubl_cii_format = 'oioubl_201' # default format for French partners is facturx
        with self.assertRaisesRegex(UserError, "The company registry is required for french partner:"):
            self.create_post_and_send_invoice(partner=self.partner_c)

    @freeze_time('2017-01-01')
    def test_oioubl_export_partner_without_vat_number(self):
        """ This test verifies that we can't export an OIOUBL file for a partner
            who doesn't have a tax ID. It verifies that we receive a UserError
            telling to the user that this field is missing.
        """
        self.partner_b.vat = None
        self.partner_b.ubl_cii_format = 'oioubl_201' # default format recomputes when vat is changed
        with self.assertRaises(UserError) as exception:
            self.create_post_and_send_invoice(partner=self.partner_b)
        self.assertIn(f"The field '{self.partner_b._fields['vat'].string}' is required", exception.exception.args[0])

    #########
    # IMPORT
    #########

    def import_bill_xml_file_in_purchase_journal(self, file_path):
        file_path = f"{self.test_module}/tests/test_files/{file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_invoice.xml',
                'raw': file.read(),
            })
        purchase_journal = self.company_data["default_journal_purchase"]
        invoice = purchase_journal._create_document_from_attachment(xml_attachment.id)
        return invoice

    @freeze_time('2017-01-01')
    def test_oioubl_import_exemple_file_1(self):
        file_name = 'external/ADVORD_01_01_00_Invoice_v2p1.xml'
        bill = self.import_bill_xml_file_in_purchase_journal(file_name)
        self.assertRecordValues(bill, ({
            'ref': 'A00095678',
            'invoice_date': fields.Date.from_string('2006-04-10'),
            'amount_total': 6_250.00,
        },))
        self.assertRecordValues(bill.invoice_line_ids, ({
            'name': 'Fine toy',
            'quantity': 1,
            'price_unit': 5_000.00,
            'price_subtotal': 5_000.00,
            'price_total': 6_250.00,
            'tax_ids': self.dk_local_purchase_tax_goods.ids,
        },))

    @freeze_time('2017-01-01')
    def test_oioubl_import_exemple_file_2(self):
        file_name = 'external/ADVORD_02_02_00_Invoice_v2p1.xml'
        bill = self.import_bill_xml_file_in_purchase_journal(file_name)
        self.assertRecordValues(bill, ({
            'ref': 'A00095680',
            'invoice_date': fields.Date.from_string('2006-04-10'),
            'amount_total': 5_000.00,
        },))
        self.assertRecordValues(bill.invoice_line_ids, ({
            'name': 'Superble',
            'quantity': 800,
            'price_unit': 5.00,
            'price_subtotal': 4_000.00,
            'price_total': 5_000.00,
            'tax_ids': self.dk_local_purchase_tax_goods.ids,
        },))

    @freeze_time('2017-01-01')
    def test_oioubl_import_exemple_file_3(self):
        file_name = 'external/ADVORD_03_03_00_Invoice_v2p1.xml'
        bill = self.import_bill_xml_file_in_purchase_journal(file_name)
        self.assertRecordValues(bill, ({
            'ref': 'A00095678',
            'invoice_date': fields.Date.from_string('2006-04-10'),
            'amount_total': 6_250.00,
        },))
        self.assertRecordValues(bill.invoice_line_ids, ({
            'name': 'Konsulentrapport',
            'quantity': 1,
            'price_unit': 5_000.00,
            'price_subtotal': 5_000.00,
            'price_total': 6_250.00,
            'tax_ids': self.dk_local_purchase_tax_goods.ids,
        },))

    @freeze_time('2017-01-01')
    def test_oioubl_import_exemple_file_4(self):
        file_name = 'external/BASPRO_01_01_00_Invoice_v2p1.xml'
        bill = self.import_bill_xml_file_in_purchase_journal(file_name)
        self.assertRecordValues(bill, ({
            'ref': 'A00095678',
            'invoice_date': fields.Date.from_string('2005-11-20'),
            'amount_total': 6_312.50,
        },))
        self.assertRecordValues(bill.invoice_line_ids, ({
            'name': 'Hejsetavle',
            'quantity': 1,
            'price_unit': 5_000.00,
            'price_subtotal': 5_000.00,
            'price_total': 6_250.00,
            'tax_ids': self.dk_local_purchase_tax_goods.ids,
        }, {
            'name': 'Beslag',
            'quantity': 2,
            'price_unit': 25.00,
            'price_subtotal': 50.00,
            'price_total': 62.50,
            'tax_ids': self.dk_local_purchase_tax_goods.ids,
        }))
