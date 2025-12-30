from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiBECommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUblCiiAllowanceCharge(TestUblCiiBECommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Buyer for UBL
        cls.buyer_ubl_bis3 = cls.partner_be.copy()
        cls.buyer_ubl_bis3.name = 'Buyer UBL BIS3'
        cls.buyer_ubl_bis3.ubl_cii_format = 'ubl_bis3'

        # Buyer for CII
        cls.buyer_facturx = cls.partner_be.copy()
        cls.buyer_facturx.name = 'Buyer FacturX'
        cls.buyer_facturx.ubl_cii_format = 'facturx'

        # Regular Percentage Tax
        cls.tax_20 = cls.env['account.tax'].create({
            'name': 'tax_20',
            'amount_type': 'percent',
            'amount': 20,
            'type_tax_use': 'sale',
        })

        # Fixed Charge
        cls.fixed_charge = cls.env['account.tax'].create({
            'name': 'Fixed Charge',
            'amount_type': 'fixed',
            'amount': 50,
            'type_tax_use': 'sale',
            'ubl_cii_type': 'allowance_charge',
            'ubl_cii_charge_reason_code': 'AA',
        })

        # Line Discount Allowance
        cls.line_discount_allowance = cls.env['account.tax'].create({
            'name': 'Line Discount Allowance',
            'amount_type': 'percent',
            'amount': -5.0,
            'type_tax_use': 'sale',
            'ubl_cii_type': 'allowance_charge',
            'ubl_cii_allowance_reason_code': '95',
            'ubl_cii_allowance_charge_reason': 'Line Discount Allowance Reason',
        })

        # Variable Allowance (Special Rebate)
        cls.rebate_allowance = cls.env['account.tax'].create({
            'name': 'Special Rebate Allowance',
            'amount_type': 'percent',
            'amount': -15.0,
            'type_tax_use': 'sale',
            'ubl_cii_type': 'allowance_charge',
            'ubl_cii_allowance_reason_code': '100',
            'ubl_cii_allowance_charge_reason': 'Special Rebate',
        })

        # Variable Charge (Rents and Leases)
        cls.rent_and_lease_charge = cls.env['account.tax'].create({
            'name': 'Rent and Lease Charge',
            'amount_type': 'percent',
            'amount': 5.0,
            'type_tax_use': 'sale',
            'ubl_cii_type': 'allowance_charge',
            'ubl_cii_charge_reason_code': 'AEF',
            'ubl_cii_allowance_charge_reason': 'Rents and Leases',
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].write({
            'email': "info@company.beexample.com",
            'phone': "+32 470 12 34 56",
        })
        return res

    def _generate_invoice(self, **invoice_args):
        return self._create_invoice_one_line(
            move_type='out_invoice',
            invoice_date='2017-01-01',
            invoice_payment_term_id=self.pay_terms_b.id,
            product_id=self.product_a.id,
            quantity=10.0,
            price_unit=100.0,
            post=True,
            **invoice_args,
        )

    def subfolder(self):
        return 'from_odoo'

    def test_01_ubl_fixed_charge(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_ubl_bis3,
            tax_ids=[(6, 0, self.tax_20.ids + self.fixed_charge.ids)],
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_01_ubl_fixed_charge')

        imported_invoice = self._import_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)

    def test_02_ubl_line_discount_allowance(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_ubl_bis3,
            tax_ids=[(6, 0, self.tax_20.ids + self.line_discount_allowance.ids)],
            discount=10.0,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_02_ubl_line_discount_allowance')

        imported_invoice = self._import_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_03_ubl_variable_allowance_charge(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_ubl_bis3,
            tax_ids=[(6, 0, self.tax_20.ids + self.rebate_allowance.ids + self.rent_and_lease_charge.ids)],
            discount=10.0,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_03_ubl_variable_allowance_charge')

        imported_invoice = self._import_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_04_ubl_allowance_charge_mixed(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_ubl_bis3,
            tax_ids=[(6, 0, (
                self.tax_20.ids
                + self.rebate_allowance.ids
                + self.line_discount_allowance.ids
                + self.rent_and_lease_charge.ids
                + self.fixed_charge.ids
            ))],
            discount=10.0,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_04_ubl_allowance_charge_mixed')

        imported_invoice = self._import_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_05_cii_fixed_charge(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_facturx,
            tax_ids=[(6, 0, self.tax_20.ids + self.fixed_charge.ids)],
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_05_cii_fixed_charge')

        imported_invoice = self._import_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)

    def test_06_cii_variable_allowance_charge(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_facturx,
            tax_ids=[(6, 0, self.tax_20.ids + self.rebate_allowance.ids + self.rent_and_lease_charge.ids)],
            discount=10.0,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_06_cii_variable_allowance_charge')

        imported_invoice = self._import_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_07_cii_allowance_charge_mixed(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_facturx,
            tax_ids=[(6, 0, (
                self.tax_20.ids
                + self.rebate_allowance.ids
                + self.rent_and_lease_charge.ids
                + self.fixed_charge.ids
            ))],
            discount=10.0,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_07_cii_allowance_charge_mixed')

        imported_invoice = self._import_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)
