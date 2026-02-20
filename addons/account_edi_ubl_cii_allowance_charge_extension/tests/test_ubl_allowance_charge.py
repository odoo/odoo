from odoo.addons.account_edi_ubl_cii_allowance_charge_extension.tests.common import TestAllowanceChargeCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUblAllowanceCharge(TestAllowanceChargeCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # seller
        cls.seller = cls.env['res.partner'].create({
            'name': "Seller",
            'street': "Street",
            'zip': "987654",
            'city': "Ramillies",
            'vat': 'BE0246697724',
            'country_id': cls.env.ref('base.be').id,
        })

        # buyer
        cls.buyer = cls.env['res.partner'].create({
            'name': "Buyer",
            'street': "Street 1",
            'zip': "123456",
            'city': "Antwerp",
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
        })

    def test_01_ubl_fixed_charge(self):
        invoice = self._generate_move(
            self.seller,
            self.buyer,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_20.ids + self.fixed_charge.ids)],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            invoice.ubl_cii_xml_id,
            xpaths='',
            expected_file_path='ubl/test_01_ubl_fixed_charge.xml',
        )
        self._assert_imported_invoice_from_etree(invoice, attachment)

    def test_02_ubl_line_discount_allowance(self):
        invoice = self._generate_move(
            self.seller,
            self.buyer,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_20.ids + self.line_discount_allowance.ids)],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            invoice.ubl_cii_xml_id,
            xpaths='',
            expected_file_path='ubl/test_02_ubl_line_discount_allowance.xml',
        )
        self._assert_imported_invoice_from_etree(invoice, attachment)

    def test_03_ubl_variable_allowance_charge(self):
        invoice = self._generate_move(
            self.seller,
            self.buyer,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_20.ids + self.rebate_allowance.ids + self.rent_and_lease_charge.ids)],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            invoice.ubl_cii_xml_id,
            xpaths='',
            expected_file_path='ubl/test_03_ubl_variable_allowance_charge.xml',
        )
        self._assert_imported_invoice_from_etree(invoice, attachment)

    def test_04_ubl_allowance_charge_mixed(self):
        invoice = self._generate_move(
            self.seller,
            self.buyer,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'discount': 10.0,
                    'tax_ids': [
                        (6, 0, (self.tax_20.ids
                                + self.rebate_allowance.ids
                                + self.line_discount_allowance.ids
                                + self.rent_and_lease_charge.ids
                                + self.fixed_charge.ids))
                    ],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            invoice.ubl_cii_xml_id,
            xpaths='',
            expected_file_path='ubl/test_04_ubl_allowance_charge_mixed.xml',
        )
        self._assert_imported_invoice_from_etree(invoice, attachment)
