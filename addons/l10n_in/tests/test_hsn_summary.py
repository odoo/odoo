from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestHSNsummary(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(chart_template_ref='in')

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

        cls.gst_5 = cls.env['account.chart.template'].ref('sgst_sale_5')
        cls.gst_18 = cls.env['account.chart.template'].ref('sgst_sale_18')
        cls.igst_0 = cls.env['account.chart.template'].ref('igst_sale_0')
        cls.igst_5 = cls.env['account.chart.template'].ref('igst_sale_5')
        cls.igst_18 = cls.env['account.chart.template'].ref('igst_sale_18')
        cls.cess_5_plus_1591 = cls.env['account.chart.template'].ref('cess_5_plus_1591_sale')
        cls.exempt_0 = cls.env['account.chart.template'].ref('exempt_sale')

    def _add_test_py_results(self, test):
        params = test['params']
        if params['test'] == 'l10n_in_hsn_summary':
            test['py_results'] = self.env['account.tax']._l10n_in_get_hsn_summary_table(params['base_lines'], params['display_uom'])
        else:
            super()._add_test_py_results(test)

    def _assert_sub_test_l10n_in_hsn_summary(self, test, results):
        expected_values = test['expected_values']
        self.assertEqual(
            {k: len(v) if k == 'items' else v for k, v in results.items()},
            {k: len(v) if k == 'items' else v for k, v in expected_values.items()},
        )
        self.assertEqual(len(results['items']), len(expected_values['items']))
        for item, expected_item in zip(results['items'], expected_values['items']):
            self.assertDictEqual(item, expected_item)

    def _assert_sub_test(self, test, results):
        params = test['params']
        if params['test'] == 'l10n_in_hsn_summary':
            self._assert_sub_test_l10n_in_hsn_summary(test, results)
        else:
            super()._assert_sub_test(test, results)

    def create_base_line_dict(self, l10n_in_hsn_code, quantity, price_unit, uom, taxes=None, product=None):
        AccountTax = self.env['account.tax']
        taxes_data = (taxes or AccountTax)._convert_to_dict_for_taxes_computation()
        product_fields = AccountTax._eval_taxes_computation_prepare_product_fields(taxes_data)
        default_product_values = AccountTax._eval_taxes_computation_prepare_product_default_values(product_fields)
        product_values = AccountTax._eval_taxes_computation_prepare_product_values(
            default_product_values=default_product_values,
            product=product,
        )
        return {
            'l10n_in_hsn_code': l10n_in_hsn_code,
            'quantity': quantity,
            'price_unit': price_unit,
            'product_values': product_values,
            'uom': {'id': uom.id, 'name': uom.name},
            'taxes_data': taxes_data,
        }

    def _prepare_l10n_in_hsn_summary_test(self, base_lines, display_uom, expected_values):
        return {
            'expected_values': expected_values,
            'params': {
                'test': 'l10n_in_hsn_summary',
                'base_lines': base_lines,
                'display_uom': display_uom,
            },
        }

    def test_l10n_in_hsn_summary_1(self):
        """ Test GST/IGST taxes. """
        tests = []
        base_lines1 = [
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 100.0, self.uom_unit, self.gst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 600.0, self.uom_unit, self.gst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 5.0, 300.0, self.uom_unit, self.gst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 100.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 600.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 5.0, 300.0, self.uom_unit, self.gst_18),
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines1,
            False,
            {
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
            },
        ))

        # Change the UOM of the second line.
        base_lines2 = [
            base_lines1[0],
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 12000.0, self.uom_dozen, self.gst_5),
        ] + base_lines1[2:]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines2,
            False,
            {
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
            },
        ))

        # Change GST 5% taxes to IGST.
        base_lines3 = [
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 100.0, self.uom_unit, self.igst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 12000.0, self.uom_dozen, self.igst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 5.0, 300.0, self.uom_unit, self.igst_5),
        ] + base_lines1[3:]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines3,
            False,
            {
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
            },
        ))

        # Put back the UOM of the second line to unit.
        base_lines4 = [
            base_lines3[0],
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 600.0, self.uom_unit, self.igst_5),
        ] + base_lines3[2:]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines4,
            False,
            {
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
            },
        ))

        # Change GST 18% taxes to IGST.
        base_lines5 = base_lines4[:3] + [
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 100.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 600.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 5.0, 300.0, self.uom_unit, self.igst_18),
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines5,
            False,
            {
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
            },
        ))
        self._assert_tests(tests)

    def test_l10n_in_hsn_summary_2(self):
        """ Test CESS taxes in combination with GST/IGST. """
        tests = []

        # Need the tax to be evaluated at the end.
        self.cess_5_plus_1591.sequence = 100

        base_lines1 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 15.80, self.uom_unit, self.gst_18 + self.cess_5_plus_1591),
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines1,
            False,
            {
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
            },
        ))

        # Change GST 18% taxes to IGST.
        base_lines2 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 15.80, self.uom_unit, self.igst_18 + self.cess_5_plus_1591),
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines2,
            False,
            {
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
            },
        ))
        self._assert_tests(tests)

    def test_l10n_in_hsn_summary_3(self):
        """ Test with mixed HSN codes. """
        tests = []
        base_lines1 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 100.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 50.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_2, 1.0, 100.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_2, 2.0, 50.0, self.uom_unit, self.gst_18),
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines1,
            False,
            {
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
            },
        ))

        # Change GST 18% taxes to IGST.
        base_lines2 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 100.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 50.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_2, 1.0, 100.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_2, 2.0, 50.0, self.uom_unit, self.igst_18),
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines2,
            False,
            {
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
            },
        ))
        self._assert_tests(tests)

    def test_l10n_in_hsn_summary_4(self):
        """ Zero rated GST or no taxes at all."""
        tests = []
        base_lines1 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, self.uom_unit),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, self.uom_unit),
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines1,
            False,
            {
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
            },
        ))

        # No tax to IGST 0%/exempt.
        base_lines2 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, self.uom_unit, self.igst_0),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, self.uom_unit, self.exempt_0),
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines2,
            False,
            {
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
            },
        ))

        # Put one IGST 18% to get a value on the IGST column.
        base_lines3 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, self.uom_unit, self.igst_18),
            base_lines2[1],
        ]
        tests.append(self._prepare_l10n_in_hsn_summary_test(
            base_lines3,
            False,
            {
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
            },
        ))
        self._assert_tests(tests)
