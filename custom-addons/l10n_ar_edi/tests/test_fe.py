# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from . import common


@tagged('fe', 'ri', 'external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestFe(common.TestEdi):

    @classmethod
    def setUpClass(cls):
        super(TestFe, cls).setUpClass('wsfe')
        cls.partner = cls.res_partner_adhoc
        cls.journal = cls._create_journal(cls, 'wsfe')
        cls._create_test_invoices_like_demo(cls)

    def test_00_connection(self):
        self._test_connection()

    def test_01_consult_invoice(self):
        self._test_consult_invoice()

    def test_02_invoice_a_product(self):
        self._test_case('invoice_a', 'product')

    def test_03_invoice_a_service(self):
        self._test_case('invoice_a', 'service')

    def test_04_invoice_a_product_service(self):
        self._test_case('invoice_a', 'product_service')

    def test_05_invoice_b_product(self):
        self._test_case('invoice_b', 'product')

    def test_06_invoice_b_service(self):
        self._test_case('invoice_b', 'service')

    def test_07_invoice_b_product_service(self):
        self._test_case('invoice_b', 'product_service')

    def test_08_credit_note_a_product(self):
        invoice = self._test_case('invoice_a', 'product')
        self._test_case_credit_note('credit_note_a', invoice)

    def test_09_credit_note_a_service(self):
        invoice = self._test_case('invoice_a', 'service')
        self._test_case_credit_note('credit_note_a', invoice)

    def test_10_credit_note_a_product_service(self):
        invoice = self._test_case('invoice_a', 'product_service')
        self._test_case_credit_note('credit_note_a', invoice)

    def test_11_credit_note_b_product(self):
        invoice = self._test_case('invoice_b', 'product')
        self._test_case_credit_note('credit_note_b', invoice)

    def test_12_credit_note_b_service(self):
        invoice = self._test_case('invoice_b', 'service')
        self._test_case_credit_note('credit_note_b', invoice)

    def test_13_credit_note_b_product_service(self):
        invoice = self._test_case('invoice_b', 'product_service')
        self._test_case_credit_note('credit_note_b', invoice)

    def test_14_corner_cases(self):
        """ Mono partner of tipe Service and VAT 21 """
        self._post(self.demo_invoices['test_invoice_1'])

    def test_15_corner_cases(self):
        """ Exento partner with multiple VAT types 21, 27 and 10,5 """
        self._post(self.demo_invoices['test_invoice_2'])

    def test_16_corner_cases(self):
        """ RI partner with VAT 0 and 21 """
        self._post(self.demo_invoices['test_invoice_3'])

    def test_17_corner_cases(self):
        """ RI partner with VAT exempt and 21 """
        self._post(self.demo_invoices['test_invoice_4'])

    def test_18_corner_cases(self):
        """ RI partner with all type of taxes """
        self._post(self.demo_invoices['test_invoice_5'])

    def test_19_corner_cases(self):
        """ Consumidor Final """
        self._post(self.demo_invoices['test_invoice_8'])

    def test_20_corner_cases(self):
        """ RI partner with many lines in order to prove rounding error, with 4 decimals of precision for the currency
        and 2 decimals for the product the error appears """
        self._post(self.demo_invoices['test_invoice_11'])

    def test_21_corner_cases(self):
        """ RI partner with many lines in order to test rounding error, it is required to use a 4 decimal precision in
        product in order to the error occur """
        self._post(self.demo_invoices['test_invoice_12'])

    def test_22_corner_cases(self):
        """ RI partner with many lines in order to test zero amount invoices y rounding error. it is required to set the
        product decimal precision to 4 and change 260.59 for 260.60 in order to reproduce the error' """
        self._post(self.demo_invoices['test_invoice_13'])

    def test_23_corner_cases(self):
        """ RI partner with 100%% of discount """
        self._post(self.demo_invoices['test_invoice_17'])

    def test_24_corner_cases(self):
        """ RI partner with 100%% of discount and with different VAT aliquots """
        self._post(self.demo_invoices['test_invoice_18'])

    def test_25_currency(self):
        """ RI in USD and VAT 21 """
        self._prepare_multicurrency_values()
        self._post(self.demo_invoices['test_invoice_10'])

    def test_26_iibb_sales_ars(self):
        iibb_tax = self._search_tax('percepcion_iibb_ba')
        iibb_tax.active = True

        product_27 = self.service_iva_27
        product_no_gravado = self.product_no_gravado
        product_exento = self.product_iva_exento

        invoice = self._create_invoice(data={
            'lines': [{'product': product_27, 'price_unit': 100.0, 'quantity': 8},
                      {'product': product_no_gravado, 'price_unit': 750.0, 'quantity': 1},
                      {'product': product_exento, 'price_unit': 40.0, 'quantity': 20}]})

        # Add perceptions taxes
        invoice.invoice_line_ids.filtered(lambda x: x.product_id == product_27).tax_ids = [(4, iibb_tax.id)]
        invoice.invoice_line_ids.filtered(lambda x: x.product_id == product_exento).tax_ids = [(4, iibb_tax.id)]

        self.assertIn(iibb_tax.name, invoice.invoice_line_ids.mapped('tax_ids').mapped('name'))
        self._validate_and_review(invoice)

    def test_27_iibb_sales_usd(self):
        iibb_tax = self._search_tax('percepcion_iibb_ba')
        iibb_tax.active = True

        self._prepare_multicurrency_values()
        invoice = self._create_invoice({'currency': self.env.ref('base.USD')})
        invoice.invoice_line_ids.filtered(lambda x: x.tax_ids).tax_ids = [(4, iibb_tax.id)]
        self.assertIn(iibb_tax.name, invoice.invoice_line_ids.mapped('tax_ids').mapped('name'))
        self._validate_and_review(invoice)

    def test_28_vendor_bill_verify(self):

        # SetUp
        self.partner = self.res_partner_adhoc
        self.journal = self._create_journal('wsfe')

        # Create a customer invoice in "Responsable Inscripto" Company to "Monotributista" Company
        invoice = self._create_invoice({'partner': self.company_mono.partner_id})
        self._validate_and_review(invoice)

        # Login in "Monotributista" Company
        self.env.user.write({'company_id': self.company_mono.id})
        self._create_afip_connections(self.company_mono, 'wscdc', 'test_cert2.crt')

        # Create a vendor bill with the same values of "Responsable Inscripto"
        bill = self._create_invoice({
            'lines': [{'price_unit': invoice.amount_total}], 'document_number': invoice.l10n_latam_document_number},
            invoice_type='in_invoice')

        # Set CAE type and number to be able to verify in AFIP
        bill.l10n_ar_afip_auth_mode = 'CAE'
        bill.l10n_ar_afip_auth_code = invoice.l10n_ar_afip_auth_code

        # Verify manually vendor bill in AFIP from "Responsable Inscripto" in "Monotributista" Company
        self.assertFalse(bill.l10n_ar_afip_verification_result)
        self._l10n_ar_verify_on_afip(bill)

        self.assertTrue(bill.l10n_ar_afip_verification_result)
        # Need to use a real CUIT to be able to verify vendor bills in AFIP, that is why we receive Rejected
        self.assertEqual(bill.l10n_ar_afip_verification_result, 'R', bill.message_ids[0].body)
