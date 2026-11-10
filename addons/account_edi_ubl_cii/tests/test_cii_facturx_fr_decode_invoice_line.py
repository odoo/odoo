from odoo.addons.account_edi_ubl_cii.tests.test_cii_import_facturx_fr import CiiImportFacturXFR
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCiiImportFacturXFRInvoiceLine(CiiImportFacturXFR):

    def test_partial_import_invoice_line_line_extension_amount(self):
        # gross_price = 1000
        # allowance_on_gross = 100
        # net_price = 900
        # charge = 50
        # line_total_amount = 950 (including charge)
        # subtotal = line_total_amount - charge = 900
        # qty = subtotal / net_price = 1
        # price_unit = net_price + allowance_on_gross + charge / qty = 900 + 100 + 50 = 1050
        # discount_percentage = (allowance_on_gross / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.5238095238095,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount(self):
        # gross_price = 200
        # allowance_on_gross = 20
        # net_price = 180
        # charge = 50
        # line_total_amount = 950 (including charge)
        # subtotal = line_total_amount - charge = 900
        # qty = subtotal / net_price = 900 / 180 = 5
        # charge_per_unit = charge / qty = 10
        # price_unit = net_price + allowance_on_gross + charge_per_unit = 180 + 20 + 10 = 210
        # discount_percentage = (allowance_on_gross / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount_and_amount(self):
        # gross_price = 250
        # allowance_on_gross = 70
        # net_price = 180
        # charge = 50
        # line_total_amount = 950 (including charge)
        # subtotal = line_total_amount - charge = 900
        # qty = subtotal / net_price = 900 / 180 = 5
        # charge_per_unit = charge / qty = 10
        # price_unit = net_price + allowance_on_gross + charge_per_unit = 180 + 70 + 10 = 260
        # discount_percentage = (allowance_on_gross / price_unit) * 100 = 26.923...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount_and_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 260.00,
                'quantity': 5.0,
                'discount': 26.92307692307695,
            },
        ])

    def test_partial_import_invoice_line_line_extension_amount_full_price_node_no_invoiced_quantity(self):
        # net_price = 1000
        # net_qty = 5
        # gross_price = 1250
        # gross_qty = 5
        # allowance_on_gross = 250
        # line_total_amount = 1000
        # allowance_per_unit = 250 / qty = 50
        # gross_price_per_unit = 1250 / 5 = 250 = price_unit
        # discount_percentage = (allowance_per_unit / price_unit) * 100 = 20
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_full_price_node_no_invoiced_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 250.00,
                'quantity': 5.0,
                'discount': 20.0,
            },
        ])

    def test_partial_import_invoice_line_line_extension_amount_full_price_node_and_invoiced_quantity(self):
        # net_price = 1000
        # net_qty = 5
        # gross_price = 1250
        # gross_qty = 5
        # allowance_on_gross = 250
        # billed_qty = 6
        # line_total_amount = 1200
        # allowance_per_unit = 250 / gross_qty = 50
        # gross_price_per_unit = 1250 / 5 = 250 = price_unit
        # discount_percentage = (allowance_per_unit / price_unit) * 100 = 20
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_full_price_node_and_invoiced_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'price_unit': 250.00,
                'quantity': 6.0,
                'discount': 20.0,
            },
        ])

    def test_partial_import_invoice_line_line_extension_amount_quantity(self):
        # billed_qty = 5
        # gross_price = 200
        # allowance_on_gross = 20
        # net_price = 180
        # charge = 50
        # line_total_amount = 950 (including charge)
        # charge_per_unit = charge / qty = 50 / 5 = 10
        # price_unit = net_price + allowance_on_gross + charge_per_unit = 180 + 20 + 10 = 210
        # discount_percentage = (allowance_on_gross / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_amount(self):
        # gross_price = 200
        # allowance_on_gross = 20
        # net_price = 180
        # charge = 50
        # line_total_amount = 950 (including charge)
        # subtotal = line_total_amount - charge = 900
        # qty = subtotal / net_price = 900 / 180 = 5
        # charge_per_unit = charge / qty = 50 / 5 = 10
        # price_unit = net_price + allowance_on_gross + charge_per_unit = 180 + 20 + 10 = 210
        # discount_percentage = (allowance_on_gross / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_zero_quantity(self):
        # billed_qty = 0 --> ignored, qty computed from the net price
        # gross_price = 1000
        # allowance_on_gross = 100
        # net_price = 900
        # charge = 50
        # line_total_amount = 950 (including charge)
        # subtotal = line_total_amount - charge = 900
        # qty = subtotal / net_price = 1
        # price_unit = net_price + allowance_on_gross + charge / qty = 900 + 100 + 50 = 1050
        # discount_percentage = (allowance_on_gross / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_zero_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_zero_quantity_zero_price_amount(self):
        # billed_qty = 0, net_price = 0 --> no price information, qty = 1
        # charge = 50
        # allowance = 100 (line allowance, not a discount)
        # line_total_amount = 950 (including allowance and charge)
        # subtotal = line_total_amount - (charge - allowance) = 950 + 50 = 1000
        # price_unit = subtotal + (charge - allowance) = 1000 - 50 = 950
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_zero_quantity_zero_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 950.00,
            'quantity': 1.0,
        }])

    def test_partial_import_invoice_line_price_amount_base_quantity(self):
        # gross_price = 1000
        # allowance_on_gross = 100
        # net_price = 900
        # gross_qty = net_qty = 5
        # charge = 50
        # line_total_amount = 950 (including charge)
        # subtotal = line_total_amount - charge = 900
        # qty = subtotal * net_qty / net_price = 900 * 5 / 900 = 5
        # net_price_per_unit = 900 / 5 = 180
        # allowance_per_unit = 100 / 5 = 20
        # charge_per_unit = 50 / 5 = 10
        # price_unit = net_price_per_unit + allowance_per_unit + charge_per_unit = 180 + 20 + 10 = 210
        # discount_percentage = (allowance_per_unit / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_price_amount_base_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_price_unit_precision(self):
        # Line 1: price = 0.043, basis_qty = 1, billed_qty = 2000, line_total_amount = 0.043 * 2000 = 86.00
        # Line 2: price = 10.00 for 3 units, billed_qty = 3, line_total_amount = 10.00
        # price_unit = 10 / 3 => price_subtotal = 3.333333 * 3 = 10.00
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_price_unit_precision')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {'price_unit': 0.043, 'quantity': 2000.0, 'discount': 0.0, 'price_subtotal': 86.00},
            {'price_unit': 10 / 3, 'quantity': 3.0, 'discount': 0.0, 'price_subtotal': 10.00},
        ])

    def test_partial_import_invoice_line_negative_lines_and_total(self):
        # as TaxBasisTotalAmount < 0, refund --> document_sign = -1
        # Line 1
        # net_price = 400 = gross_price = price_unit (bc no charge/allowance)
        # billed_qty = -7
        # line_total_amount = -2800
        # price_unit = 400
        # qty = billed_qty * document_sign = 7
        # Line 2
        # net_price = 500 = gross_price = price_unit (bc no charge/allowance)
        # billed_qty = 3
        # line_total_amount = 1500
        # price_unit = 500
        # qty = billed_qty * document_sign = -3
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

    def test_partial_import_invoice_discount_on_price_zero(self):
        imported_invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_discount_on_price_zero')
        self.assertRecordValues(imported_invoice, [{
            'amount_total': 1.73,
            'payment_reference': 'INV/2026/00001',
        }])
        self.assertRecordValues(imported_invoice.invoice_line_ids, [{
            'label': self.product_a.name,
            'price_subtotal': 1.5,
            'price_unit': 1.5,
            'discount': 0.0,
        }])
