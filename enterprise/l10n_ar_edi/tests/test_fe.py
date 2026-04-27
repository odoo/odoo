# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import skip_unless_external
from odoo.addons.l10n_ar_edi.tests.common import TestArEdiCommon
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install', *TestArEdiCommon.extra_tags)
class TestArEdiWsfe(TestArEdiCommon):

    @classmethod
    @TestArEdiCommon.setup_afip_ws('wsfe')
    def setUpClass(cls):
        super().setUpClass()
        cls.subfolder = "wsfe/normal"
        cls.partner = cls.res_partner_adhoc
        cls.journal = cls._create_journal('wsfe')
        cls._create_test_invoices_like_demo()

    @skip_unless_external
    def test_ar_edi_wsfe_external_flow(self):
        self._test_ar_edi_common_external()

    def test_ar_edi_wsfe_flow_suite(self):
        for test_name, move_type, document_code, concept in (
                ('test_wsfe_invoice_a_product', 'invoice', 'a', 'product'),
                ('test_wsfe_invoice_a_service', 'invoice', 'a', 'service'),
                ('test_wsfe_invoice_a_product_service', 'invoice', 'a', 'product_service'),
                ('test_wsfe_invoice_b_product', 'invoice', 'b', 'product'),
                ('test_wsfe_invoice_b_service', 'invoice', 'b', 'service'),
                ('test_wsfe_invoice_b_product_service', 'invoice', 'b', 'product_service'),
                ('test_wsfe_credit_note_a_product', 'credit_note', 'a', 'product'),
                ('test_wsfe_credit_note_a_service', 'credit_note', 'a', 'service'),
                ('test_wsfe_credit_note_a_product_service', 'credit_note', 'a', 'product_service'),
                ('test_wsfe_credit_note_b_product', 'credit_note', 'b', 'product'),
                ('test_wsfe_credit_note_b_service', 'credit_note', 'b', 'service'),
                ('test_wsfe_credit_note_b_product_service', 'credit_note', 'b', 'product_service'),
        ):
            with self.subTest(test_name=test_name), self.cr.savepoint() as sp:
                self._test_ar_edi_flow(test_name, move_type, document_code, concept)
                sp.close()  # Rollback to ensure all subtests start in the same situation

    def test_ar_edi_wsfe_corner_cases(self):
        for demo_invoice_key in (
                'test_invoice_1',  # Mono partner of type Service and VAT 21
                'test_invoice_2',  # Exento partner with multiple VAT types 21, 27 and 10,5
                'test_invoice_3',  # RI partner with VAT 0 and 21
                'test_invoice_4',  # RI partner with VAT exempt and 21
                'test_invoice_5',  # RI partner with all type of taxes
                'test_invoice_8',  # Consumidor Final

                # RI partner with many lines in order to prove rounding error (with 4 decimals of precision):
                'test_invoice_11',  # -> rounding of 4 decimals on the currency and 2 decimals for the product
                'test_invoice_12',  # -> standard
                'test_invoice_13',  # -> standard, but change 260.59 for 260.60
                'test_invoice_17',  # -> 100%% of discount
                'test_invoice_18',  # -> 100%% of discount with different VAT aliquots
        ):
            with self.subTest(demo_invoice_key=demo_invoice_key):
                self._post(self.demo_invoices[demo_invoice_key])

    def test_ar_edi_wsfe_multicurrency(self):
        """ RI in USD and VAT 21 """
        self._prepare_multicurrency_values()
        self._post(self.demo_invoices['test_invoice_10'])

    def test_ar_edi_wsfe_iibb_sales_ars(self):
        iibb_tax = self._search_tax('percepcion_iibb_ba')
        iibb_tax.active = True

        product_27 = self.service_iva_27
        product_no_gravado = self.product_no_gravado
        product_exento = self.product_iva_exento

        invoice = self._create_invoice_ar(
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100.0, product_id=product_27, quantity=8),
                self._prepare_invoice_line(price_unit=750.0, product_id=product_no_gravado, quantity=1),
                self._prepare_invoice_line(price_unit=40.0, product_id=product_exento, quantity=20),
            ],
        )

        # Add perceptions taxes
        invoice.invoice_line_ids.filtered(lambda x: x.product_id == product_27).tax_ids = [(4, iibb_tax.id)]
        invoice.invoice_line_ids.filtered(lambda x: x.product_id == product_exento).tax_ids = [(4, iibb_tax.id)]

        self.assertIn(iibb_tax.name, invoice.invoice_line_ids.mapped('tax_ids').mapped('name'))
        self._validate_and_review(invoice, "test_wsfe_iibb_sales_ars")

    def test_ar_edi_wsfe_iibb_sales_usd(self):
        iibb_tax = self._search_tax('percepcion_iibb_ba')
        iibb_tax.active = True

        self._prepare_multicurrency_values()
        invoice = self._create_invoice_ar(currency_id=self.env.ref('base.USD'))
        invoice.invoice_line_ids.filtered(lambda x: x.tax_ids).tax_ids = [(4, iibb_tax.id)]
        self.assertIn(iibb_tax.name, invoice.invoice_line_ids.mapped('tax_ids').mapped('name'))
        self._validate_and_review(invoice, "test_wsfe_iibb_sales_usd")

    def test_ar_edi_wsfe_vendor_bill_verify(self):
        # Create a customer invoice in "Responsable Inscripto" Company to "Monotributista" Company
        invoice = self._create_invoice_ar(partner_id=self.company_mono.partner_id)
        self._validate_and_review(invoice, "test_wsfe_verify_invoice")

        # Login in "Monotributista" Company
        self.env.user.write({'company_id': self.company_mono.id})
        if 'external' in self.test_tags:
            self.company_mono.write({'l10n_ar_afip_ws_crt_id': self.ar_certificate_2})
            self._create_afip_connections(self.company_mono, 'wscdc')

        # Create a vendor bill with the same values of "Responsable Inscripto"
        bill = self._create_invoice_ar(
            invoice_line_ids=[self._prepare_invoice_line(price_unit=invoice.amount_total, product_id=self.product_iva_21)],
            l10n_latam_document_number=invoice.l10n_latam_document_number,
            move_type='in_invoice',
        )

        # Set CAE type and number to be able to verify in AFIP
        bill.l10n_ar_afip_auth_mode = 'CAE'
        bill.l10n_ar_afip_auth_code = invoice.l10n_ar_afip_auth_code

        # Verify manually vendor bill in AFIP from "Responsable Inscripto" in "Monotributista" Company
        self.assertFalse(bill.l10n_ar_afip_verification_result)
        if 'external' in self.test_tags:
            with self._handler_afip_internal_error():
                bill.l10n_ar_verify_on_afip()

            self.assertTrue(bill.l10n_ar_afip_verification_result)
            # Need to use a real CUIT to be able to verify vendor bills in AFIP, that is why we receive Rejected
            self.assertEqual(bill.l10n_ar_afip_verification_result, 'R', bill.message_ids[0].body)
        else:
            verify_request_data = bill._l10n_ar_edi_get_request_data_verify()
            self.assert_json(verify_request_data, 'test_wsfe_verify_bill', 'wsfe/bill')

    def test_ar_edi_wsfe_payment_foreign_currency(self):
        """ Payment in Foreign Currency  """
        self._test_payment_foreign_currency()

    def test_ar_edi_wsfe_rounding_complex(self):
        custom_invoice_line_ids = [
            self._prepare_invoice_line(price_unit=100.545, tax_ids=self.tax_21, discount=25.0),
            self._prepare_invoice_line(price_unit=100.545, tax_ids=self.tax_21, discount=25.0),
            self._prepare_invoice_line(price_unit=100.545, tax_ids=self.tax_21, discount=25.0),
            self._prepare_invoice_line(price_unit=100.545, tax_ids=self.tax_21, discount=25.0),
        ]

        with self.subTest('invoice_a'), self.cr.savepoint() as sp:
            self.env.company.tax_calculation_rounding_method = 'round_globally'
            invoice_a = self._create_invoice_ar(invoice_line_ids=custom_invoice_line_ids)
            self._validate_and_review(invoice_a, "test_wsfe_round_01")
            sp.close()

        with self.subTest('invoice_b'):
            self.env.company.tax_calculation_rounding_method = 'round_per_line'
            invoice_b = self._create_invoice_ar(invoice_line_ids=custom_invoice_line_ids)
            self._validate_and_review(invoice_b, "test_wsfe_round_02")
