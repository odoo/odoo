from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nInHSNSummary(TestTaxCommon):

    @classmethod
    @TestTaxCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()

        cls.test_hsn_code_1 = '1234'
        cls.test_hsn_code_2 = '4321'

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')

        cls.product_a.l10n_in_hsn_code = cls.test_hsn_code_1
        cls.product_b.l10n_in_hsn_code = cls.test_hsn_code_2
        cls.product_c = cls.env['product.product'].create({
            'name': 'product_c',
            'l10n_in_hsn_code': cls.test_hsn_code_1,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
        })

        ChartTemplate = cls.env['account.chart.template']
        cls.gst_5 = ChartTemplate.ref('sgst_sale_5')
        cls.gst_18 = ChartTemplate.ref('sgst_sale_18')
        cls.igst_0 = ChartTemplate.ref('igst_sale_0')
        cls.igst_5 = ChartTemplate.ref('igst_sale_5')
        cls.igst_18 = ChartTemplate.ref('igst_sale_18')
        cls.cess_5_plus_1591 = ChartTemplate.ref('cess_5_plus_1591_sale')
        cls.exempt_0 = ChartTemplate.ref('exempt_sale')
        cls.igst_18_rc = ChartTemplate.ref('igst_sale_18_rc')

    def _jsonify_tax(self, tax):
        # EXTENDS 'account.
        values = super()._jsonify_tax(tax)
        values['l10n_in_tax_type'] = tax.l10n_in_tax_type
        return values

    def _jsonify_document_line(self, document, index, line):
        # EXTENDS 'account.
        values = super()._jsonify_document_line(document, index, line)
        values['l10n_in_hsn_code'] = line['l10n_in_hsn_code']
        return values

    def convert_base_line_to_invoice_line(self, document, base_line):
        # EXTENDS 'account.
        values = super().convert_base_line_to_invoice_line(document, base_line)
        values['l10n_in_hsn_code'] = base_line['l10n_in_hsn_code']
        return values

    # -------------------------------------------------------------------------
    # l10n_in_hsn_summary
    # -------------------------------------------------------------------------

    def _assert_sub_test_l10n_in_hsn_summary(self, results, expected_values):
        self.assertEqual(
            {k: len(v) if k == 'items' else v for k, v in results['hsn'].items()},
            {k: len(v) if k == 'items' else v for k, v in expected_values.items()},
        )
        self.assertEqual(len(results['hsn']['items']), len(expected_values['items']))
        for item, expected_item in zip(results['hsn']['items'], expected_values['items']):
            self.assertDictEqual(item, expected_item)

    def _create_py_sub_test_l10n_in_hsn_summary(self, document, display_uom):
        return {
            'hsn': self.env['account.tax']._l10n_in_get_hsn_summary_table(document['lines'], display_uom),
        }

    def _create_js_sub_test_l10n_in_hsn_summary(self, document, display_uom):
        return {
            'test': 'l10n_in_hsn_summary',
            'document': self._jsonify_document(document),
            'display_uom': display_uom,
        }

    def assert_l10n_in_hsn_summary(
        self,
        document,
        expected_values,
        display_uom=False,
    ):
        self._create_assert_test(
            expected_values,
            self._create_py_sub_test_l10n_in_hsn_summary,
            self._create_js_sub_test_l10n_in_hsn_summary,
            self._assert_sub_test_l10n_in_hsn_summary,
            document,
            display_uom,
        )

    # -------------------------------------------------------------------------
    # invoice l10n_in_hsn_summary
    # -------------------------------------------------------------------------

    def assert_invoice_l10n_in_hsn_summary(self, invoice, expected_values):
        results = {'hsn': {
            **invoice._l10n_in_get_hsn_summary_table(),
            # 'display_uom' is just checking if the user has the uom group. It's irrelevant to test it.
            'display_uom': expected_values['display_uom'],
        }}
        self._assert_sub_test_l10n_in_hsn_summary(results, expected_values)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def create_base_line_dict(self, l10n_in_hsn_code, quantity, price_unit, discount, uom, taxes=None, product=None):
        return {
            'l10n_in_hsn_code': l10n_in_hsn_code,
            'quantity': quantity,
            'price_unit': price_unit,
            'discount': discount,
            'product': product,
            'uom': uom,
            'taxes_data': taxes or self.env['account.tax'],
        }

    def _test_l10n_in_hsn_summary_1(self):
        """ Test GST/IGST taxes. """
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 600.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 600.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
        ]))
        expected_values = {
            'has_igst': False,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 7,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 8.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 5.0,
                    'amount_untaxed': 2300.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 57.5,
                    'tax_amount_sgst': 57.5,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 8.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 2300.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 207.0,
                    'tax_amount_sgst': 207.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 1, document, expected_values

        # Another UOM on the second line.
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 12000.0,  'product_uom_id': self.uom_dozen,   'tax_ids': self.gst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 600.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
        ]))
        expected_values = {
            'has_igst': False,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 7,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 7.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 5.0,
                    'amount_untaxed': 1700.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 42.5,
                    'tax_amount_sgst': 42.5,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_dozen.name,
                    'rate': 5.0,
                    'amount_untaxed': 12000.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 300.0,
                    'tax_amount_sgst': 300.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 8.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 2300.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 207.0,
                    'tax_amount_sgst': 207.0,
                    'tax_amount_cess': 0.0,
                }
            ]
        }
        yield 2, document, expected_values

        # Change GST 5% taxes to IGST.
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 12000.0,  'product_uom_id': self.uom_dozen,   'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 600.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
        ]))
        expected_values = {
            'has_igst': True,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 8,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 7.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 5.0,
                    'amount_untaxed': 1700.0,
                    'tax_amount_igst': 85.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_dozen.name,
                    'rate': 5.0,
                    'amount_untaxed': 12000.0,
                    'tax_amount_igst': 600.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 8.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 2300.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 207.0,
                    'tax_amount_sgst': 207.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 3, document, expected_values

        # Put back the UOM of the second line to unit.
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 600.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 600.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
        ]))
        expected_values = {
            'has_igst': True,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 8,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 8.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 5.0,
                    'amount_untaxed': 2300.0,
                    'tax_amount_igst': 115.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 8.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 2300.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 207.0,
                    'tax_amount_sgst': 207.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 4, document, expected_values

        # Change GST 18% taxes to IGST.
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 600.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_5},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 600.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 5.0,    'price_unit': 300.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18},
        ]))
        expected_values = {
            'has_igst': True,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 6,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 8.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 5.0,
                    'amount_untaxed': 2300.0,
                    'tax_amount_igst': 115.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 8.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 2300.0,
                    'tax_amount_igst': 414.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 5, document, expected_values

    def test_l10n_in_hsn_summary_1_generic_helpers(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_1():
            with self.subTest(test_index=test_index):
                self.assert_l10n_in_hsn_summary(document, expected_values)
        self._run_js_tests()

    def test_l10n_in_hsn_summary_1_invoices(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_1():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_l10n_in_hsn_summary(invoice, expected_values)

    def _test_l10n_in_hsn_summary_2(self):
        """ Test CESS taxes in combination with GST/IGST. """
        # Need the tax to be evaluated at the end.
        self.cess_5_plus_1591.sequence = 100

        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1, 'quantity': 1.0, 'price_unit': 15.80, 'product_uom_id': self.uom_unit, 'tax_ids': self.gst_18 + self.cess_5_plus_1591},
        ]))
        expected_values = {
            'has_igst': False,
            'has_gst': True,
            'has_cess': True,
            'nb_columns': 8,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 15.8,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 1.42,
                    'tax_amount_sgst': 1.42,
                    'tax_amount_cess': 2.38,
                },
            ],
        }
        yield 1, document, expected_values

        # Change GST 18% taxes to IGST.
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 15.80,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18 + self.cess_5_plus_1591},
        ]))
        expected_values = {
            'has_igst': True,
            'has_gst': False,
            'has_cess': True,
            'nb_columns': 7,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 15.8,
                    'tax_amount_igst': 2.84,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 2.38,
                },
            ],
        }
        yield 2, document, expected_values

    def test_l10n_in_hsn_summary_2_generic_helpers(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_2():
            with self.subTest(test_index=test_index):
                self.assert_l10n_in_hsn_summary(document, expected_values)
        self._run_js_tests()

    def test_l10n_in_hsn_summary_2_invoices(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_2():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_l10n_in_hsn_summary(invoice, expected_values)

    def _test_l10n_in_hsn_summary_3(self):
        """ Test with mixed HSN codes. """
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 50.0,     'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_2,  'quantity': 1.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_2,  'quantity': 2.0,    'price_unit': 50.0,     'product_uom_id': self.uom_unit,    'tax_ids': self.gst_18},
        ]))
        expected_values = {
            'has_igst': False,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 7,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 3.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 200.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 18.0,
                    'tax_amount_sgst': 18.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_2,
                    'quantity': 3.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 200.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 18.0,
                    'tax_amount_sgst': 18.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 1, document, expected_values

        # Change GST 18% taxes to IGST.
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 2.0,    'price_unit': 50.0,     'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_2,  'quantity': 1.0,    'price_unit': 100.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_2,  'quantity': 2.0,    'price_unit': 50.0,     'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18},
        ]))
        expected_values = {
            'has_igst': True,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 6,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 3.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 200.0,
                    'tax_amount_igst': 36.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_2,
                    'quantity': 3.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 200.0,
                    'tax_amount_igst': 36.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 2, document, expected_values

    def test_l10n_in_hsn_summary_3_generic_helpers(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_3():
            with self.subTest(test_index=test_index):
                self.assert_l10n_in_hsn_summary(document, expected_values)
        self._run_js_tests()

    def test_l10n_in_hsn_summary_3_invoices(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_3():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_l10n_in_hsn_summary(invoice, expected_values)

    def _test_l10n_in_hsn_summary_4(self):
        """ Zero rated GST or no taxes at all."""
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 350.0,    'product_uom_id': self.uom_unit},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 350.0,    'product_uom_id': self.uom_unit},
        ]))
        expected_values = {
            'has_igst': False,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 5,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 2.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 0.0,
                    'amount_untaxed': 700.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 1, document, expected_values

        # No tax to IGST 0%/exempt.
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 350.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_0},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 350.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.exempt_0},
        ]))
        expected_values = {
            'has_igst': False,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 5,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 2.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 0.0,
                    'amount_untaxed': 700.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 2, document, expected_values

        # Put one IGST 18% to get a value on the IGST column.
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 350.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.igst_18},
            {'l10n_in_hsn_code': self.test_hsn_code_1,  'quantity': 1.0,    'price_unit': 350.0,    'product_uom_id': self.uom_unit,    'tax_ids': self.exempt_0},
        ]))
        expected_values = {
            'has_igst': True,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 6,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 350.0,
                    'tax_amount_igst': 63.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 0.0,
                    'amount_untaxed': 350.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 3, document, expected_values

    def test_l10n_in_hsn_summary_4_generic_helpers(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_4():
            with self.subTest(test_index=test_index):
                self.assert_l10n_in_hsn_summary(document, expected_values)
        self._run_js_tests()

    def test_l10n_in_hsn_summary_4_invoices(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_4():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_l10n_in_hsn_summary(invoice, expected_values)

    def _test_l10n_in_hsn_summary_5(self):
        """ Test with discount. """
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1, 'quantity': 1.0, 'price_unit': 100.0, 'discount': 10.0, 'product_uom_id': self.uom_unit},
        ]))
        expected_values = {
            'has_igst': False,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 5,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 0.0,
                    'amount_untaxed': 90.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 1, document, expected_values

    def test_l10n_in_hsn_summary_5_generic_helpers(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_5():
            with self.subTest(test_index=test_index):
                self.assert_l10n_in_hsn_summary(document, expected_values)
        self._run_js_tests()

    def test_l10n_in_hsn_summary_5_invoices(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_5():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_l10n_in_hsn_summary(invoice, expected_values)

    def _test_l10n_in_hsn_summary_6(self):
        """ Test with Sale RC tax. """
        document = self.populate_document(self.init_document([
            {'l10n_in_hsn_code': self.test_hsn_code_1, 'quantity': 1.0, 'price_unit': 100.0, 'product_uom_id': self.uom_unit, 'tax_ids': self.igst_18_rc},
        ]))
        expected_values = {
            'has_igst': True,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 6,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 18.0,
                    'amount_untaxed': 100.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        }
        yield 1, document, expected_values

    def test_l10n_in_hsn_summary_6_generic_helpers(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_6():
            with self.subTest(test_index=test_index):
                self.assert_l10n_in_hsn_summary(document, expected_values)
        self._run_js_tests()

    def test_l10n_in_hsn_summary_6_invoices(self):
        for test_index, document, expected_values in self._test_l10n_in_hsn_summary_6():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_l10n_in_hsn_summary(invoice, expected_values)

    def test_l10n_in_hsn_summary_manual_edit_invoice_taxes(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.gst_5.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'l10n_in_hsn_code': self.test_hsn_code_2,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.gst_5.ids)],
                }),
            ],
        })

        # Manual edition of the tax.
        sgst_tax = self.gst_5.children_tax_ids.filtered(lambda tax: tax.l10n_in_tax_type == 'sgst')
        cgst_tax = self.gst_5.children_tax_ids.filtered(lambda tax: tax.l10n_in_tax_type == 'cgst')
        tax_line_sgst = invoice.line_ids.filtered(lambda aml: aml.tax_line_id == sgst_tax)
        tax_line_cgst = invoice.line_ids.filtered(lambda aml: aml.tax_line_id == cgst_tax)
        payment_term = invoice.line_ids.filtered(lambda aml: aml.display_type == 'payment_term')
        invoice.line_ids = [
            Command.update(tax_line_sgst.id, {'amount_currency': tax_line_sgst.amount_currency + 1.0}),
            Command.update(tax_line_cgst.id, {'amount_currency': tax_line_cgst.amount_currency + 1.0}),
            Command.update(payment_term.id, {'amount_currency': payment_term.amount_currency - 2.0}),
        ]

        self.assert_invoice_l10n_in_hsn_summary(invoice, {
            'has_igst': False,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 7,
            'display_uom': False,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 5.0,
                    'amount_untaxed': 1000.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 24.5,
                    'tax_amount_sgst': 24.5,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_2,
                    'quantity': 1.0,
                    'uom_name': self.uom_unit.name,
                    'rate': 5.0,
                    'amount_untaxed': 1000.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 24.5,
                    'tax_amount_sgst': 24.5,
                    'tax_amount_cess': 0.0,
                },
            ],
        })
