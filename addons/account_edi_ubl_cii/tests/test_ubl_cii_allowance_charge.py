from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiBECommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAllowanceChargeCommon(TestUblCiiBECommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Fixed Charge
        cls.fixed_charge = cls._create_allowance_charge_tax(
            name='Fixed Charge',
            amount_type='fixed',
            amount=50.0,
            reason_code='AA',
            reason='',
            is_charge=True,
            is_emptying=False,
            type_tax_use='sale',
        )

        # Line Discount Allowance
        cls.line_discount_allowance = cls._create_allowance_charge_tax(
            name='Line Discount Allowance',
            amount_type='percent',
            amount=-5.0,
            reason_code='95',
            reason='Line Discount Allowance Reason',
            is_charge=False,
            is_emptying=False,
            type_tax_use='sale',
        )

        # Variable Allowance (Special Rebate)
        cls.rebate_allowance = cls._create_allowance_charge_tax(
            name='Special Rebate Allowance',
            amount_type='percent',
            amount=-15.0,
            reason_code='100',
            reason='Special Rebate',
            is_charge=False,
            is_emptying=False,
            type_tax_use='sale',
        )

        # Variable Charge (Rents and Leases)
        cls.rent_and_lease_charge = cls._create_allowance_charge_tax(
            name='Rent and Lease Charge',
            amount_type='percent',
            amount=5.0,
            reason_code='AEF',
            reason='Rents and Leases',
            is_charge=True,
            is_emptying=False,
            type_tax_use='sale',
        )

        # Telecommunications
        cls.telecommunications = cls._create_allowance_charge_tax(
            name='Telecommunications',
            amount_type='percent',
            amount=20.0,
            reason_code='AAA',
            reason='Telecommunications',
            is_charge=True,
            is_emptying=False,
            type_tax_use='sale',
        )

        # Regular Percentage Tax
        cls.tax_20 = cls.env['account.tax'].create({
            'name': 'tax_20',
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'sale',
            'ubl_cii_tax_category_code': 'S',
        })

    @classmethod
    def _create_company(cls, **create_values):
        company = super()._create_company(**create_values)
        company.write({
            'email': "info@company.beexample.com",
            'phone': "+32 470 12 34 56",
        })
        return company

    def _generate_invoice(self, **invoice_args):
        return self._create_invoice_one_line(
            move_type='out_invoice',
            invoice_date='2026-03-01',
            invoice_payment_term_id=self.pay_terms_b.id,
            product_id=self.product_a.id,
            quantity=10.0,
            price_unit=100.0,
            post=True,
            **invoice_args,
        )


@tagged('post_install', '-at_install')
class TestBis3AllowanceCharge(TestAllowanceChargeCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Buyer for UBL
        cls.buyer_ubl_bis3 = cls.partner_be.copy()
        cls.buyer_ubl_bis3.name = 'Buyer UBL BIS3'
        cls.buyer_ubl_bis3.invoice_edi_format = 'ubl_bis3'

    @classmethod
    def subfolders(cls):
        return 'bis3', 'invoice', 'be'

    def test_ubl_fixed_charge(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_ubl_bis3,
            tax_ids=[(6, 0, self.tax_20.ids + self.fixed_charge.ids)],
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_ubl_fixed_charge')

        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)

    def test_ubl_line_discount_allowance(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_ubl_bis3,
            tax_ids=[(6, 0, self.tax_20.ids + self.line_discount_allowance.ids)],
            discount=10.0,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_ubl_line_discount_allowance')

        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_ubl_variable_allowance_charge(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_ubl_bis3,
            tax_ids=[(6, 0, self.tax_20.ids + self.rebate_allowance.ids + self.rent_and_lease_charge.ids)],
            discount=10.0,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_ubl_variable_allowance_charge')

        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_ubl_allowance_charge_mixed(self):
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
        self._assert_invoice_ubl_file(invoice, 'test_ubl_allowance_charge_mixed')

        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_ubl_allowance_charge_correct_import_amount_tax(self):
        '''When same amount regular and allowance/charge taxes are imported,
        invoice amount_tax should include allowance/charge correctly.'''
        imported_invoice = self._import_invoice_as_attachment_on(
            test_name='test_ubl_allowance_charge_correct_import_amount_tax',
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.amount_tax, 440.00)

    def test_ubl_allowance_charge_insufficient_tax(self):
        '''When some allowance/charge tax is not found in system,
        we ignore other found taxes and adjust it against `price_unit`.'''
        imported_invoice = self._import_invoice_as_attachment_on(
            test_name='test_ubl_allowance_charge_insufficient_tax',
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(len(imported_invoice.invoice_line_ids.tax_ids), 1)

    def test_ubl_allowance_charge_correct_import_algo(self):
        '''To ensure that import algorithm is working correctly'''
        imported_invoice = self._import_invoice_as_attachment_on(
            test_name='test_ubl_allowance_charge_correct_import_algo',
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(len(imported_invoice.invoice_line_ids.tax_ids), 3)


@tagged('post_install', '-at_install')
class TestCiiAllowanceCharge(TestAllowanceChargeCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Buyer for CII
        cls.buyer_facturx = cls.partner_be.copy()
        cls.buyer_facturx.name = 'Buyer FacturX'
        cls.buyer_facturx.invoice_edi_format = 'facturx'

    @classmethod
    def subfolders(cls):
        return 'cii', 'invoice', 'be'

    def test_cii_fixed_charge(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_facturx,
            tax_ids=[(6, 0, self.tax_20.ids + self.fixed_charge.ids)],
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_cii_fixed_charge')

        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)

    def test_cii_variable_allowance_charge(self):
        invoice = self._generate_invoice(
            partner_id=self.buyer_facturx,
            tax_ids=[(6, 0, self.tax_20.ids + self.rebate_allowance.ids + self.rent_and_lease_charge.ids)],
            discount=10.0,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_cii_variable_allowance_charge')

        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_cii_allowance_charge_mixed(self):
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
        self._assert_invoice_ubl_file(invoice, 'test_cii_allowance_charge_mixed')

        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=invoice.ubl_cii_xml_id,
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.tax_ids, invoice.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(imported_invoice.invoice_line_ids.discount, invoice.invoice_line_ids.discount)

    def test_cii_allowance_charge_insufficient_tax(self):
        '''When some allowance/charge tax is not found in system,
        we ignore other found taxes and adjust it against `price_unit`.'''
        imported_invoice = self._import_invoice_as_attachment_on(
            test_name='test_cii_allowance_charge_insufficient_tax',
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(len(imported_invoice.invoice_line_ids.tax_ids), 1)

    def test_cii_allowance_charge_correct_import_algo(self):
        '''To ensure that import algorithm is working correctly'''
        imported_invoice = self._import_invoice_as_attachment_on(
            test_name='test_cii_allowance_charge_correct_import_algo',
            journal=self.company_data["default_journal_sale"],
        )
        self.assertEqual(len(imported_invoice.invoice_line_ids.tax_ids), 3)
