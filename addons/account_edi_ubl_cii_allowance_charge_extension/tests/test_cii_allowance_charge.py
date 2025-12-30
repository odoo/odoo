from odoo.addons.account_edi_ubl_cii_allowance_charge_extension.tests.common import TestAllowanceChargeCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUblAllowanceCharge(TestAllowanceChargeCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Seller partner
        cls.seller = cls.env['res.partner'].create({
            'name': "Seller",
            'street': "Street 1",
            'zip': "987654",
            'city': "Paris",
            'vat': 'FR05677404089',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {
                'acc_number': 'FR15001559627230',
                'allow_out_payment': True,
            })],
            'phone': '+1 (650) 555-0111',
            'email': "seller@yourcompany.com",
        })

        # Buyer partner
        cls.buyer = cls.env['res.partner'].create({
            'name': "Buyer",
            'street': "Street 1",
            'zip': "123456",
            'city': "Lyon",
            'vat': 'FR35562153452',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {
                'acc_number': 'FR90735788866632',
                'allow_out_payment': True,
            })],
        })

    def test_01_cii_fixed_charge(self):
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
            expected_file_path='cii/test_01_cii_fixed_charge.xml',
        )
        self._assert_imported_invoice_from_etree(invoice, attachment)

    def test_02_cii_variable_allowance_charge(self):
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
            expected_file_path='cii/test_02_cii_variable_allowance_charge.xml',
        )
        self._assert_imported_invoice_from_etree(invoice, attachment)

    def test_03_cii_allowance_charge_mixed(self):
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
                                + self.rent_and_lease_charge.ids
                                + self.fixed_charge.ids))
                    ],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            invoice.ubl_cii_xml_id,
            xpaths='',
            expected_file_path='cii/test_03_cii_allowance_charge_mixed.xml',
        )
        self._assert_imported_invoice_from_etree(invoice, attachment)
