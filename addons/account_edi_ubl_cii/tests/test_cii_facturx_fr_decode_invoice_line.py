from odoo.addons.account_edi_ubl_cii.tests.test_cii_import_facturx_fr import CiiImportFacturXFR
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCiiImportFacturXFRInvoiceLine(CiiImportFacturXFR):

    def test_partial_import_invoice_line_line_extension_amount(self):
        # charge = 50
        # allowance = 100
        # line_total_amount = 950 (including allowance and charge)
        # gross_price = line_total_amount + allowance - charge = 950 + 100 - 50 = 1000
        # price_unit = gross_price + charge = 1050
        # discount = allowance --> discount_percentage = (allowance / price_unit) * 100
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.5238095238095,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount(self):
        # net_price = gross_price = 200
        # charge = 50
        # allowance = 100
        # line_total_amount = 950 (including allowance and charge)
        # net_price = (line_total_amount + allowance - charge) / qty
        # qty = (950 + 100 - 50) / 200 = 5
        # charge_per_unit = charge / qty = 10
        # unit_price = gross_price + charge_per_unit = 210
        # discount_percentage = (allowance_per_unit / unit_price) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_allowance_base_amount_and_amount(self):
        # gross_price = 250
        # allowance_on_gross = 50
        # net_price = 200
        # charge = 50
        # total_allowance = 100
        # line_total_amount = 950 (including allowance and charge)
        # net_price = (line_total_amount + allowance - charge) / qty
        # qty = (950 + 100 - 50) / 200 = 5
        # allowance_per_unit = allowance_on_gross + total_allowance / qty = 50 + 100 / 5 = 70
        # charge_per_unit = charge / qty = 10
        # unit_price = gross_price + charge_per_unit = 260
        # discount_percentage = (allowance_per_unit / unit_price) * 100 = 26.923...
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
        # total_charge = 50
        # total_allowance = 100
        # line_total_amount = 950
        # gross_price = (line_total_amount + allowance - charge) / qty
        # gross_price = 1000 / 5 = 200 (= gross_price_unit bc gross_unit = 1)
        # allowance_per_unit = total_allowance / qty = 20
        # charge_per_unit = total_charge / qty = 50 / 5 = 10
        # price_unit = gross_price + charge_per_unit = 210
        # discount_percentage = (allowance_per_unit / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_price_amount(self):
        # net_amount = 200
        # total_charge = 50
        # total_allowance = 100
        # line_total_amount = 950
        # net_price = (line_total_amount + allowance - charge) / qty
        # qty = 1000 / 200 = 5
        # gross_price = 1000 / 5 = 200
        # allowance_per_unit = total_allowance / qty = 20
        # charge_per_unit = total_charge / qty = 50 / 5 = 10
        # price_unit = gross_price_unit + charge_per_unit = 210
        # discount_percentage = (allowance_per_unit / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_zero_quantity(self):
        # charge = 50
        # allowance = 100
        # line_total_amount = 950 (including allowance and charge)
        # gross_price = line_total_amount + allowance - charge = 950 + 100 - 50 = 1000
        # price_unit = gross_price + charge = 1050
        # discount_percentage = (allowance / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_zero_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_line_extension_amount_zero_quantity_zero_price_amount(self):
        # charge = 50
        # allowance = 100
        # line_total_amount = 950 (including allowance and charge)
        # gross_price = line_total_amount + allowance - charge = 950 + 100 - 50 = 1000
        # price_unit = gross_price + charge = 1050
        # discount_percentage = (allowance / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_line_extension_amount_zero_quantity_zero_price_amount')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 1050.00,
            'quantity': 1.0,
            'discount': 9.52380952380953,
        }])

    def test_partial_import_invoice_line_price_amount_base_quantity(self):
        # net_price = 1000
        # net_qty = 5
        # net_price_per_unit = 1000 / 5 = 200
        # charge = 50
        # allowance = 100
        # line_total_amount = 950 (including allowance and charge)
        # gross_price = line_total_amount + allowance - charge = 950 + 100 - 50 = 1000
        # gross_price_per_unit = 1000 / 5 = 200
        # charge_per_unit = 50 / 5 = 10
        # price_unit = gross_price_per_unit + charge_per_unit = 210
        # allowance_per_unit = 100 / 5 = 20
        # discount_percentage = (allowance_per_unit / price_unit) * 100 = 9.523809...
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_invoice_line_price_amount_base_quantity')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 210.00,
            'quantity': 5.0,
            'discount': 9.52380952380953,
        }])

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
        self.assertRecordValues(imported_invoice, [{'amount_total': 1.73}])
        self.assertRecordValues(imported_invoice.invoice_line_ids, [{
            'name': self.product_a.name,
            'price_subtotal': 1.5,
            'price_unit': 2.0,
            'discount': 25.0,
        }])
