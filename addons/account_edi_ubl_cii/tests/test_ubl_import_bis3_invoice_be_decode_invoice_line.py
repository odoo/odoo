from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBEDecodeInvoiceLine(TestUblImportBis3InvoiceBE):

    def test_partial_import_invoice_line_name_and_description(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_name_and_description')
        self.assertRecordValues(invoice.invoice_line_ids, [{'name': 'description value'}])

    def test_partial_import_invoice_line_name(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_name')
        self.assertRecordValues(invoice.invoice_line_ids, [{'name': 'name value'}])

    def test_partial_import_invoice_line_line_extension_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.523809523809524,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.523809523809524,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount_and_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount_and_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 260.00,
                'quantity': 5.0,
                'discount': 26.923076923076923,
            },
        ])

    def test_partial_import_invoice_line_line_extension_amount_price_allowance_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_allowance_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 260.00,
                'quantity': 5.0,
                'discount': 26.923076923076923,
            },
        ])

    def test_partial_import_invoice_line_line_extension_amount_full_price_node_no_invoiced_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_full_price_node_no_invoiced_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 250.00,
                'quantity': 5.0,
                'discount': 20.0,
            },
        ])

    def test_partial_import_invoice_line_line_extension_amount_full_price_node_and_invoiced_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_full_price_node_and_invoiced_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 250.00,
                'quantity': 6.0,
                'discount': 20.0,
            },
        ])

    def test_partial_import_invoice_line_line_extension_amount_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.523809523809524,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.523809523809524,
        }])

    def test_partial_import_invoice_line_line_extension_amount_zero_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_zero_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.523809523809524,
        }])

    def test_partial_import_invoice_line_line_extension_amount_zero_quantity_zero_price_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_zero_quantity_zero_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.523809523809524,
        }])

    def test_partial_import_invoice_line_price_amount_base_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_price_amount_base_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.523809523809524,
        }])

    def test_partial_import_invoice_line_price_amount_base_quantity_invoiced_quantity_different_uom(self):
        # net_price = 1€ for 2L
        # gross_price = 2€ for 2L (allowance on price = 1€)
        # net_price per liter = 0.5€
        # invoiced_qty = 2m³ = 2000L
        # gross_price per m³ = 2 * 1000 / 2 = 1000€
        # charge = 50 => charge per m³ = 25 => price_unit = 1025
        # allowance = 100 + price allowance (1 * 1000 / 2 * 2 = 1000) = 1100
        # discount = 1100 / (1025 * 2) * 100 = 53.658...
        # line extension amount = 0.5 * 2000 - 100 + 50 = 950
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_price_amount_base_quantity_invoiced_quantity_different_uom')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1025.0,
            'quantity': 2.0,
            'product_uom_id': self.ref('uom.product_uom_cubic_meter'),
            'discount': 53.65853658536585,
            'price_subtotal': 950.0,
        }])

    def test_partial_import_invoice_line_price_amount_base_quantity_invoiced_quantity_smaller_uom(self):
        # gross_price = 1000€ per m³, price allowance = 500€ => net_price = 500€ per m³ = 0.5€ per L
        # billed_qty = 2000L
        # price_unit = 1€ + charge per L (50 / 2000) = 1.025€
        # discount = (100 + 500 * 2) / (1.025 * 2000) * 100 = 53.658...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_price_amount_base_quantity_invoiced_quantity_smaller_uom')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1.025,
            'quantity': 2000.0,
            'product_uom_id': self.ref('uom.product_uom_litre'),
            'discount': 53.65853658536585,
            'price_subtotal': 950.0,
        }])

    def test_partial_import_invoice_line_negative_lines_and_total(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_negative_lines_and_total')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 400.0,
                'quantity': 7.0,
                'discount': 0.0,
                'price_subtotal': 2800.0,
            },
            {
                'price_unit': 500.0,
                'quantity': -3.0,
                'discount': 0.0,
                'price_subtotal': -1500.0,
            },
        ])

    def test_partial_import_invoice_line_zero_line_extension_amount(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_zero_line_extension_amount')
        self.assertFalse(invoice.invoice_line_ids)

    def test_partial_import_invoice_line_zero_line_extension_amount_with_quantity_allowance_charge(self):
        def assert_invoice(invoice):
            self.assertRecordValues(invoice, [{'amount_total': 0.0}])
            self.assertRecordValues(invoice.invoice_line_ids, [{
                'price_unit': 0.25,
                'quantity': 2.0,
                'discount': 100.0,
                'tax_ids': [],
                'price_subtotal': 0.0,
            }])

        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_zero_line_extension_amount_with_quantity_allowance_charge')
        assert_invoice(invoice)

        # Same test but the fixed tax will be retrieved.
        self.fixed_tax(0.25, type_tax_use='purchase')
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_zero_line_extension_amount_with_quantity_allowance_charge')
        assert_invoice(invoice)

    def test_partial_import_invoice_line_zero_line_extension_amount_zero_quantity_with_price_amount(self):
        """
        A line with LineExtensionAmount=0 and InvoicedQuantity=0 but a non-zero PriceAmount caused a division by zero.
        Such lines must be skipped without blocking the rest of the import.
        """
        # Include an extra line to distinct import error from no lines imported
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_zero_line_extension_amount_zero_quantity_with_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 100.0,
            'quantity': 1.0,
            'price_subtotal': 100.0,
        }])

    def test_import_charge_and_discount_for_price_zero(self):
        imported_invoice = self._import_invoice_as_attachment_on(test_name='test_import_invoice_discount_on_price_zero')
        self.assertRecordValues(imported_invoice, [{'amount_total': 1.73}])
        self.assertRecordValues(imported_invoice.invoice_line_ids, [{
            'name': self.product_a.name,
            'price_subtotal': 1.5,
            'price_unit': 2.0,
            'discount': 25.0,
        }])

    def test_import_invoice_line_quantity_decimals(self):
        imported_invoice = self._import_invoice_as_attachment_on(test_name='test_import_invoice_line_quantity_decimals')
        self.assertEqual(imported_invoice.invoice_line_ids[0].quantity, 1800.0)

    def test_partial_import_invoice_line_negative_with_base_quantity(self):
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_negative_with_base_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 449.32,
            'quantity': 1.0,
            'discount': 0.0,
            'price_subtotal': 449.32,
        }])

    def test_partial_import_invoice_line_with_discount_and_included_tax(self):
        self.env['account.tax'].create({
            'name': '21 included',
            'amount': 21.0,
            'amount_type': 'percent',
            'price_include_override': 'tax_included',
            'type_tax_use': 'purchase',
            'company_id': self.company_data['company'].id
        })
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_with_discount_and_included_tax')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 121.0,
                'quantity': 2.0,
                'discount': 50.0,
                'price_subtotal': 100.0,
            },
            {
                'price_unit': 121.0,
                'quantity': 1.0,
                'discount': 100.0,
                'price_subtotal': 0.0,
            }
        ])
