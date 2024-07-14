# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from . import common


@tagged('fex', 'ri', 'external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestFex(common.TestFexCommon):

    def test_00_connection(self):
        self._test_connection()

    def test_01_consult_invoice(self):
        self._test_consult_invoice()

    def test_02_invoice_e_product(self):
        """ similar to  demo_invoice_14 """
        self._test_case('invoice_e', 'product')

    def test_03_invoice_e_service(self):
        """ similar to  demo_invoice_15 """
        self._test_case('invoice_e', 'service')

    def test_04_invoice_e_product_service(self):
        self._test_case('invoice_e', 'product_service')

    def test_05_credit_note_e_product(self):
        """ similar to  demo_invoice_16 """
        invoice = self._test_case('invoice_e', 'product')
        self._test_case_credit_note('credit_note_e', invoice)

    def test_06_credit_note_e_service(self):
        invoice = self._test_case('invoice_e', 'service')
        self._test_case_credit_note('credit_note_e', invoice)

    def test_07_credit_note_e_product_service(self):
        invoice = self._test_case('invoice_e', 'product_service')
        self._test_case_credit_note('credit_note_e', invoice)

    def test_08_free_zone(self):
        """ Invoice to "IVA Liberado - Free Zone" partner (similar to demo_invoice_6) """
        partner = self.res_partner_cerrocastor
        invoice = self._test_case('invoice_e', 'product_service', forced_values={
            'partner': partner,
            'lines': [{'product': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                      {'product': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                      {'product': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                      {'product': self.product_no_gravado, 'price_unit': 50.0, 'quantity': 10},
                      {'product': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                      {'product': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1}]})
        tax_exento = self._search_tax('iva_exento')
        self.assertEqual(invoice.invoice_line_ids.mapped('tax_ids'), tax_exento)

    def test_09_invoice_e_product_service(self):
        """ Invoice "4 - Otros (expo)" because it have Services (similar to demo_invoice_7) """
        # Can be unified with test_04_invoice_e_product_service? why 4 - Otros (expo)?
        partner = self.res_partner_expresso
        invoice = self._test_case('invoice_e', 'product_service', forced_values={
            'partner': partner,
            'lines': [{'product': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                      {'product': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                      {'product': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                      {'product': self.product_no_gravado, 'price_unit': 50.0, 'quantity': 10},
                      {'product': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                      {'product': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1}]})
        tax_exento = self._search_tax('iva_exento')
        self.assertEqual(invoice.invoice_line_ids.mapped('tax_ids'), tax_exento)

    def test_10_invoice_with_notes(self):
        """ Invoice with multiple products/services and with line note """
        partner = self.res_partner_expresso
        invoice = self._test_case('invoice_e', 'product_service', forced_values={
            'partner': partner,
            'lines': [{'product': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                      {'product': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                      {'product': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                      {'product': self.product_no_gravado, 'price_unit': 50.0, 'quantity': 10},
                      {'product': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                      {'product': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1},
                      {'display_type': 'line_note', 'name': 'Notes'}
                      ]})
        tax_exento = self._search_tax('iva_exento')
        self.assertEqual(invoice.invoice_line_ids.mapped('tax_ids'), tax_exento)
