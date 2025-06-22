# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import common
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.tools.float_utils import float_split_str


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestManual(common.TestAr):

    @classmethod
    def setUpClass(cls):
        super(TestManual, cls).setUpClass()
        cls.journal = cls._create_journal(cls, 'preprinted')
        cls.partner = cls.res_partner_adhoc
        cls._create_test_invoices_like_demo(cls)

    def test_01_create_invoice(self):
        """ Create and validate an invoice for a Responsable Inscripto

        * Proper set the current user company
        * Properly set the tax amount of the product / partner
        * Proper fiscal position (this case not fiscal position is selected)
        """
        invoice = self._create_invoice()
        self.assertEqual(invoice.company_id, self.company_ri, 'created with wrong company')
        self.assertEqual(invoice.amount_tax, 21, 'invoice taxes are not properly set')
        self.assertEqual(invoice.amount_total, 121.0, 'invoice taxes has not been applied to the total')
        self.assertEqual(invoice.l10n_latam_document_type_id, self.document_type['invoice_a'], 'selected document type should be Factura A')
        self._post(invoice)
        self.assertEqual(invoice.state, 'posted', 'invoice has not been validate in Odoo')
        self.assertEqual(invoice.name, 'FA-A %05d-00000002' % self.journal.l10n_ar_afip_pos_number, 'Invoice number is wrong')

    def test_02_fiscal_position(self):
        # ADHOC SA > IVA Responsable Inscripto > Without Fiscal Positon
        invoice = self._create_invoice({'partner': self.partner})
        self.assertFalse(invoice.fiscal_position_id, 'Fiscal position should be set to empty')

        # Consumidor Final > IVA Responsable Inscripto > Without Fiscal Positon
        invoice = self._create_invoice({'partner': self.partner_cf})
        self.assertFalse(invoice.fiscal_position_id, 'Fiscal position should be set to empty')

        # Montana Sur > IVA Liberado - Ley Nº 19.640 > Compras / Ventas Zona Franca > IVA Exento
        invoice = self._create_invoice({'partner': self.res_partner_montana_sur})
        self.assertEqual(invoice.fiscal_position_id, self._search_fp('Purchases / Sales Free Trade Zone'))

        # Barcelona food > Cliente / Proveedor del Exterior >  > IVA Exento
        invoice = self._create_invoice({'partner': self.res_partner_barcelona_food})
        self.assertEqual(invoice.fiscal_position_id, self._search_fp('Purchases / Sales abroad'))

    def test_03_corner_cases(self):
        """ Mono partner of type Service and VAT 21 """
        self._post(self.demo_invoices['test_invoice_1'])

    def test_04_corner_cases(self):
        """ Exento partner with multiple VAT types 21, 27 and 10,5' """
        self._post(self.demo_invoices['test_invoice_2'])

    def test_05_corner_cases(self):
        """ RI partner with VAT 0 and 21 """
        self._post(self.demo_invoices['test_invoice_3'])

    def test_06_corner_cases(self):
        """ RI partner with VAT exempt and 21 """
        self._post(self.demo_invoices['test_invoice_4'])

    def test_07_corner_cases(self):
        """ RI partner with all type of taxes """
        self._post(self.demo_invoices['test_invoice_5'])

    def test_08_corner_cases(self):
        """ Consumidor Final """
        self._post(self.demo_invoices['test_invoice_8'])

    def test_09_corner_cases(self):
        """ RI partner with many lines in order to prove rounding error, with 4  decimals of precision for the
        currency and 2 decimals for the product the error appear """
        self._post(self.demo_invoices['test_invoice_11'])

    def test_10_corner_cases(self):
        """ RI partner with many lines in order to test rounding error, it is required  to use a 4 decimal precision
        in product in order to the error occur """
        self._post(self.demo_invoices['test_invoice_12'])

    def test_11_corner_cases(self):
        """ RI partner with many lines in order to test zero amount  invoices y rounding error. it is required to
        set the product decimal precision to 4 and change 260,59 for 260.60 in order to reproduce the error """
        self._post(self.demo_invoices['test_invoice_13'])

    def test_12_corner_cases(self):
        """ RI partner with 100%% of discount """
        self._post(self.demo_invoices['test_invoice_17'])

    def test_13_corner_cases(self):
        """ RI partner with 100%% of discount and with different VAT aliquots """
        self._post(self.demo_invoices['test_invoice_18'])

    def test_14_corner_cases(self):
        """ Responsable Inscripto" in USD and VAT 21 """
        self._prepare_multicurrency_values()
        self._post(self.demo_invoices['test_invoice_10'])

    def test_15_liquido_producto_sales(self):
        """ Manual Numbering: Sales and not POS (Liquido Producto) """

        # Verify that the default sales journals ara created as is AFIP POS
        self.assertTrue(self.journal.l10n_ar_is_pos)

        # If we create an invoice it will not use manual numbering
        invoice = self._create_invoice({'partner': self.partner})
        self.assertFalse(invoice.l10n_latam_manual_document_number)

        # Create a new sale journal that is not AFIP POS
        self.journal = self._create_journal('preprinted', data={'l10n_ar_is_pos': False})
        self.assertFalse(self.journal.l10n_ar_is_pos)

        doc_27_lu_a = self.env.ref('l10n_ar.dc_liq_uci_a')
        payment_term_id = self.env.ref("account.account_payment_term_end_following_month")

        # 60, 61, 27, 28, 45, 46
        # In this case manual numbering should be True and the latam document numer should be required
        with self.assertRaisesRegex(AssertionError, 'l10n_latam_document_number is a required field'):
            with Form(self.env['account.move'].with_context(default_move_type='out_invoice')) as invoice_form:
                invoice_form.ref = "demo_liquido_producto_1: Vendor bill liquido producto (DOC 186)"
                invoice_form.partner_id = self.res_partner_adhoc
                invoice_form.invoice_payment_term_id = payment_term_id
                invoice_form.journal_id = self.journal
                invoice_form.l10n_latam_document_type_id = doc_27_lu_a
            invoice = invoice_form.save()

        # Adding the document number will let us to save and validate the number without any problems
        with Form(self.env['account.move'].with_context(default_move_type='out_invoice')) as invoice_form:
            invoice_form.ref = "demo_liquido_producto_1: Vendor bill liquido producto (DOC 186)"
            invoice_form.partner_id = self.res_partner_adhoc
            invoice_form.invoice_payment_term_id = payment_term_id
            invoice_form.journal_id = self.journal
            invoice_form.l10n_latam_document_type_id = doc_27_lu_a
            invoice_form.l10n_latam_document_number = "00077-00000077"
        invoice = invoice_form.save()

    def test_16_liquido_producto_purchase(self):
        """ Manual Numbering: Purchase POS/ NOT POS (Liquido Producto) """

        # By default purchase journals ar not AFIP POS journal
        purchase_not_pos_journal = self.env["account.journal"].search([
            ('type', '=', 'purchase'), ('company_id', '=', self.env.company.id), ('l10n_latam_use_documents', '=', True)])
        self.assertFalse(purchase_not_pos_journal.l10n_ar_is_pos)

        doc_60_lp_a = self.env.ref('l10n_ar.dc_a_cvl')
        payment_term_id = self.env.ref("account.account_payment_term_end_following_month")

        with self.assertRaisesRegex(AssertionError, 'l10n_latam_document_number is a required field'):
            with Form(self.env['account.move'].with_context(default_move_type='in_invoice')) as bill_form:
                bill_form.ref = "demo_liquido_producto_1: Vendor bill liquido producto (DOC 186)"
                bill_form.partner_id = self.res_partner_adhoc
                bill_form.invoice_payment_term_id = payment_term_id
                bill_form.invoice_date = '2023-02-09'
                bill_form.journal_id = purchase_not_pos_journal
                bill_form.l10n_latam_document_type_id = doc_60_lp_a
            bill = bill_form.save()

        # Create a new journal that is an AFIP POS
        purchase_pos_journal = self._create_journal('preprinted', data={'type': 'purchase', 'l10n_ar_is_pos': True})

        with Form(self.env['account.move'].with_context(default_move_type='in_invoice')) as bill_form:
            bill_form.ref = "demo_liquido_producto_1: Vendor bill liquido producto (DOC 186)"
            bill_form.partner_id = self.res_partner_adhoc
            bill_form.invoice_payment_term_id = payment_term_id
            bill_form.invoice_date = '2023-02-09'
            bill_form.journal_id = purchase_pos_journal
            bill_form.l10n_latam_document_type_id = doc_60_lp_a
            bill_form.l10n_latam_document_number = "00077-00000077"
        bill = bill_form.save()

        # If we create an invoice it will not use manual numbering
        self.assertFalse(bill.l10n_latam_manual_document_number)

    def test_17_corner_cases(self):
        """ RI partner with VAT exempt and 21. Test price unit digits """
        self._post(self.demo_invoices['test_invoice_4'])
        decimal_price_digits_setting = self.env.ref('product.decimal_price').digits
        invoice_line_ids = self.demo_invoices['test_invoice_4'].invoice_line_ids
        for line in invoice_line_ids:
            l10n_ar_line_prices = line._l10n_ar_prices_and_taxes()
            _unitary_part, l10n_ar_price_unit_decimal_part = float_split_str(l10n_ar_line_prices['price_unit'], decimal_price_digits_setting)
            len_l10n_ar_price_unit_digits = len(l10n_ar_price_unit_decimal_part)
            _unitary_part, line_price_unit_decimal_part = float_split_str(line.price_unit, decimal_price_digits_setting)
            len_line_price_unit_digits = len(line_price_unit_decimal_part)
            if len_l10n_ar_price_unit_digits == len_line_price_unit_digits == decimal_price_digits_setting:
                self.assertEqual(l10n_ar_price_unit_decimal_part, line_price_unit_decimal_part)

    def _get_simple_detail_ar_tax(self, invoice):
        """ Get the simple detail_ar_tax list of tuples with the vat group name and the amount
        [("vat_taxes", float), ("other_taxes", float)] """
        return [
            (item.get('group'), item.get('tax_amount'))
            for item in invoice._l10n_ar_get_invoice_totals_for_report().get('detail_ar_tax')
        ]

    def test_16_invoice_b_tax_breakdown_1(self):
        """ Display Both VAT and Other Taxes """
        invoice1 = self._create_invoice_from_dict({
            'ref': 'test_invoice_20:  Final Consumer Invoice B with multiple vat/perceptions/internal/other/national taxes',
            "move_type": 'out_invoice',
            "partner_id": self.partner_cf,
            "company_id": self.company_ri,
            "invoice_date": "2021-03-20",
            "invoice_line_ids": [
                {'product_id': self.service_iva_21, 'price_unit': 124.3, 'quantity': 3, 'name': 'Support Services 8',
                 'tax_ids': [(6, 0, [self.tax_21.id, self.tax_perc_iibb.id])]},
                {'product_id': self.service_iva_27, 'price_unit': 2250.0, 'quantity': 1,
                    'tax_ids': [(6, 0, [self.tax_27.id, self.tax_national.id])]},
                {'product_id': self.product_iva_105_perc, 'price_unit': 1740.0, 'quantity': 1,
                    'tax_ids': [(6, 0, [self.tax_10_5.id, self.tax_internal.id])]},
                {'product_id': self.product_iva_105_perc, 'price_unit': 10000.0, 'quantity': 1,
                    'tax_ids': [(6, 0, [self.tax_0.id, self.tax_other.id])]},
            ],
        })
        self.assertEqual(self._get_simple_detail_ar_tax(invoice1), [("vat", 868.51), ("other", 142.20)])

    def test_17_invoice_b_tax_breakdown_2(self):
        """ Display only Other Taxes (VAT taxes are 0) """
        invoice2 = self._create_invoice_from_dict({
            'ref': 'test_invoice_21:  inal Consumer Invoice B with 0 tax and internal tax',
            "move_type": 'out_invoice',
            "partner_id": self.partner_cf,
            "company_id": self.company_ri,
            "invoice_date": "2021-03-20",
            "invoice_line_ids": [
                {'product_id': self.product_iva_105_perc, 'price_unit': 10000.0, 'quantity': 1,
                    'tax_ids': [(6, 0, [self.tax_no_gravado.id, self.tax_internal.id])]},
            ],
        })
        self.assertEqual(self._get_simple_detail_ar_tax(invoice2), [("vat", 0.0), ("other", 300.0)])

    def test_18_invoice_b_tax_breakdown_3(self):
        """ Display only Other Taxes (VAT taxes are 0 and non other taxes) """
        invoice3 = self._create_invoice_from_dict({
            'ref': 'test_invoice_22:  Final Consumer Invoice B with 0 only',
            "move_type": 'out_invoice',
            "partner_id": self.partner_cf,
            "company_id": self.company_ri,
            "invoice_date": "2021-03-20",
            "invoice_line_ids": [
                {'product_id': self.product_iva_105_perc, 'price_unit': 10000.0, 'quantity': 1,
                    'tax_ids': [(6, 0, [self.tax_no_gravado.id])]},
            ],
        })
        self.assertEqual(self._get_simple_detail_ar_tax(invoice3), [("vat", 0.0)])
