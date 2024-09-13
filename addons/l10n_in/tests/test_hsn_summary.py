from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestHSNsummary(TestTaxCommon):

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

        cls.gst_5 = cls.env['account.chart.template'].ref('sgst_sale_5')
        cls.gst_18 = cls.env['account.chart.template'].ref('sgst_sale_18')
        cls.igst_0 = cls.env['account.chart.template'].ref('igst_sale_0')
        cls.igst_5 = cls.env['account.chart.template'].ref('igst_sale_5')
        cls.igst_18 = cls.env['account.chart.template'].ref('igst_sale_18')
        cls.cess_5_plus_1591 = cls.env['account.chart.template'].ref('cess_5_plus_1591_sale')
        cls.exempt_0 = cls.env['account.chart.template'].ref('exempt_sale')

    def _jsonify_tax(self, tax):
        values = super()._jsonify_tax(tax)
        values['l10n_in_tax_type'] = tax.l10n_in_tax_type
        return values

    def _jsonify_uom(self, uom):
        return {
            'id': uom.id,
            'name': uom.name,
        }

    def _assert_sub_test_l10n_in_hsn_summary(self, results, expected_values):
        self.assertEqual(
            {k: len(v) if k == 'items' else v for k, v in results['hsn'].items()},
            {k: len(v) if k == 'items' else v for k, v in expected_values.items()},
        )
        self.assertEqual(len(results['hsn']['items']), len(expected_values['items']))
        for item, expected_item in zip(results['hsn']['items'], expected_values['items']):
            self.assertDictEqual(item, expected_item)

    def _create_py_sub_test_l10n_in_hsn_summary(self, base_lines, display_uom):
        return {
            'hsn': self.env['account.tax']._l10n_in_get_hsn_summary_table(base_lines, display_uom),
        }

    def _create_js_sub_test_l10n_in_hsn_summary(self, base_lines, display_uom):
        new_base_lines = []
        for base_line in base_lines:
            base_line = dict(base_line)
            taxes = base_line['taxes_data']
            base_line['taxes_data'] = [self._jsonify_tax(tax) for tax in taxes]
            base_line['product'] = self._jsonify_product(base_line['product'], taxes)
            base_line['uom'] = self._jsonify_uom(base_line['uom'])
            new_base_lines.append(base_line)
        return {
            'test': 'l10n_in_hsn_summary',
            'display_uom': display_uom,
            'base_lines': new_base_lines,
        }

    def assert_l10n_in_hsn_summary(
        self,
        base_lines,
        expected_values,
        display_uom=False,
    ):
        self._create_assert_test(
            expected_values,
            self._create_py_sub_test_l10n_in_hsn_summary,
            self._create_js_sub_test_l10n_in_hsn_summary,
            self._assert_sub_test_l10n_in_hsn_summary,
            base_lines,
            display_uom,
        )

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

    def test_l10n_in_hsn_summary_1(self):
        """ Test GST/IGST taxes. """
        base_lines1 = [
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 100.0, 0.0, self.uom_unit, self.gst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 600.0, 0.0, self.uom_unit, self.gst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 5.0, 300.0, 0.0, self.uom_unit, self.gst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 100.0, 0.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 600.0, 0.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 5.0, 300.0, 0.0, self.uom_unit, self.gst_18),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines1,
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
        )

        # Change the UOM of the second line.
        base_lines2 = [
            base_lines1[0],
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 12000.0, 0.0, self.uom_dozen, self.gst_5),
        ] + base_lines1[2:]
        self.assert_l10n_in_hsn_summary(
            base_lines2,
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
        )

        # Change GST 5% taxes to IGST.
        base_lines3 = [
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 100.0, 0.0, self.uom_unit, self.igst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 12000.0, 0.0, self.uom_dozen, self.igst_5),
            self.create_base_line_dict(self.test_hsn_code_1, 5.0, 300.0, 0.0, self.uom_unit, self.igst_5),
        ] + base_lines1[3:]
        self.assert_l10n_in_hsn_summary(
            base_lines3,
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
        )

        # Put back the UOM of the second line to unit.
        base_lines4 = [
            base_lines3[0],
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 600.0, 0.0, self.uom_unit, self.igst_5),
        ] + base_lines3[2:]
        self.assert_l10n_in_hsn_summary(
            base_lines4,
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
        )

        # Change GST 18% taxes to IGST.
        base_lines5 = base_lines4[:3] + [
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 100.0, 0.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 600.0, 0.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 5.0, 300.0, 0.0, self.uom_unit, self.igst_18),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines5,
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
        )
        self._run_js_tests()

    def test_l10n_in_hsn_summary_2(self):
        """ Test CESS taxes in combination with GST/IGST. """
        # Need the tax to be evaluated at the end.
        self.cess_5_plus_1591.sequence = 100

        base_lines1 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 15.80, 0.0, self.uom_unit, self.gst_18 + self.cess_5_plus_1591),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines1,
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
        )

        # Change GST 18% taxes to IGST.
        base_lines2 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 15.80, 0.0, self.uom_unit, self.igst_18 + self.cess_5_plus_1591),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines2,
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
        )
        self._run_js_tests()

    def test_l10n_in_hsn_summary_3(self):
        """ Test with mixed HSN codes. """
        base_lines1 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 100.0, 0.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 50.0, 0.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_2, 1.0, 100.0, 0.0, self.uom_unit, self.gst_18),
            self.create_base_line_dict(self.test_hsn_code_2, 2.0, 50.0, 0.0, self.uom_unit, self.gst_18),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines1,
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
        )

        # Change GST 18% taxes to IGST.
        base_lines2 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 100.0, 0.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_1, 2.0, 50.0, 0.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_2, 1.0, 100.0, 0.0, self.uom_unit, self.igst_18),
            self.create_base_line_dict(self.test_hsn_code_2, 2.0, 50.0, 0.0, self.uom_unit, self.igst_18),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines2,
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
        )
        self._run_js_tests()

    def test_l10n_in_hsn_summary_4(self):
        """ Zero rated GST or no taxes at all."""
        base_lines1 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, 0.0, self.uom_unit),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, 0.0, self.uom_unit),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines1,
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
        )

        # No tax to IGST 0%/exempt.
        base_lines2 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, 0.0, self.uom_unit, self.igst_0),
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, 0.0, self.uom_unit, self.exempt_0),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines2,
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
        )

        # Put one IGST 18% to get a value on the IGST column.
        base_lines3 = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 350.0, 0.0, self.uom_unit, self.igst_18),
            base_lines2[1],
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines3,
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
        )
        self._run_js_tests()

    def test_l10n_in_hsn_summary_5(self):
        """ Test with discount. """
        base_lines = [
            self.create_base_line_dict(self.test_hsn_code_1, 1.0, 100.0, 10.0, self.uom_unit),
        ]
        self.assert_l10n_in_hsn_summary(
            base_lines,
            {
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
            },
        )
        self._run_js_tests()
