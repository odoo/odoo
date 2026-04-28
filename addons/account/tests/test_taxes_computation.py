from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputation(TestTaxCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.tax_calculation_rounding_method = 'round_globally'
        cls.currency = cls.env.company.currency_id
        cls.foreign_currency = cls.setup_other_currency('EUR')
        cls.tax_groups = cls.env['account.tax.group'].create([
            {'name': str(i), 'sequence': str(i)}
            for i in range(1, 10)
        ])

    def _reverse_sign(self, tax_details_values):
        new_tax_details_values = {
            k: -v
            for k, v in tax_details_values.items()
            if k != 'taxes_data'
        }
        new_taxes_data = new_tax_details_values['taxes_data'] = []
        for tax_data in tax_details_values['taxes_data']:
            new_tax_data = {
                k: -v
                for k, v in tax_data.items()
                if k != 'tax_id'
            }
            new_tax_data['tax_id'] = tax_data['tax_id']
            new_taxes_data.append(new_tax_data)
        return new_tax_details_values

    def test_taxes_ordering(self):
        tax_division = self.division_tax(10.0, sequence=1)
        tax_fixed = self.fixed_tax(10.0, sequence=2)
        tax_percent = self.percent_tax(10.0, sequence=3)
        tax_group = self.group_of_taxes(tax_fixed + tax_percent, sequence=4)

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 200, 'tax_ids': tax_group | tax_division}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 200.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax_division.id,
                        'base_amount_currency': 200.0,
                        'tax_amount_currency': 22.22,
                    },
                    {
                        'tax_id': tax_fixed.id,
                        'base_amount_currency': 200.0,
                        'tax_amount_currency': 10.0,
                    },
                    {
                        'tax_id': tax_percent.id,
                        'base_amount_currency': 200.0,
                        'tax_amount_currency': 20.0,
                    },
                ],
            }],
            expected_base_amount=200.0,
            expected_tax_amount=52.22,
            expected_total_amount=252.22,
        )

        tax_percent1 = self.percent_tax(0.0, price_include_override='tax_included')
        tax_percent2 = self.percent_tax(8.0, price_include_override='tax_included')
        tax_group1 = self.group_of_taxes(tax_percent1, sequence=5)
        tax_group2 = self.group_of_taxes(tax_percent2, sequence=6)

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 124.4, 'tax_ids': tax_group1 | tax_group2}],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 115.19,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax_percent1.id,
                        'base_amount_currency': 115.19,
                        'tax_amount_currency': 0.0,
                    },
                    {
                        'tax_id': tax_percent2.id,
                        'base_amount_currency': 115.19,
                        'tax_amount_currency': 9.21,
                    },
                ],
            }],
            expected_base_amount=115.19,
            expected_tax_amount=9.21,
            expected_total_amount=124.4,
        )
        self._run_js_tests()

    def test_taxes_filtering(self):
        tax_percent_1 = self.percent_tax(10.0)
        tax_percent_2 = self.percent_tax(20.0)

        document = self.populate_document(self.init_document(
            lines=[{
                'price_unit': 100.0,
                'tax_ids': tax_percent_1 | tax_percent_2,
                'excluded_tax_ids': tax_percent_2.ids,
            }],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 100.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax_percent_1.id,
                        'base_amount_currency': 100.0,
                        'tax_amount_currency': 10.0,
                    },
                ],
            }],
            expected_base_amount=100.0,
            expected_tax_amount=10.0,
            expected_total_amount=110.0,
        )
        self._run_js_tests()

    def test_coupling_multiple_included_taxes(self):
        tax_percent_8_price_included = self.percent_tax(8.0, price_include_override='tax_included')
        tax_percent_0_price_included = self.percent_tax(0.0, price_include_override='tax_included')

        document = self.populate_document(self.init_document(
            lines=[{
                'price_unit': 124.4,
                'tax_ids': tax_percent_8_price_included + tax_percent_0_price_included,
            }],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 115.19,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax_percent_8_price_included.id,
                        'base_amount_currency': 115.19,
                        'tax_amount_currency': 9.21,
                    },
                    {
                        'tax_id': tax_percent_0_price_included.id,
                        'base_amount_currency': 115.19,
                        'tax_amount_currency': 0.0,
                    },
                ],
            }],
            expected_base_amount=115.19,
            expected_tax_amount=9.21,
            expected_total_amount=124.4,
        )
        self._run_js_tests()

    def test_taxes_affecting_the_base_of_others(self):
        tax_percent_20_withholding = self.percent_tax(-20.0)
        tax_percent_4 = self.percent_tax(4.0, include_base_amount=True)
        tax_percent_22 = self.percent_tax(22.0)
        taxes = tax_percent_20_withholding + tax_percent_4 + tax_percent_22

        document = self.populate_document(self.init_document(
            lines=[{
                'price_unit': 50.0,
                'tax_ids': taxes,
            }],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 50.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax_percent_20_withholding.id,
                        'base_amount_currency': 50.0,
                        'tax_amount_currency': -10.0,
                    },
                    {
                        'tax_id': tax_percent_4.id,
                        'base_amount_currency': 50.0,
                        'tax_amount_currency': 2.0,
                    },
                    {
                        'tax_id': tax_percent_22.id,
                        'base_amount_currency': 52.0,
                        'tax_amount_currency': 11.44,
                    },
                ],
            }],
            expected_base_amount=50.0,
            expected_tax_amount=3.44,
            expected_total_amount=53.44,
        )
        self._run_js_tests()

    def test_tax_division_price_included_100_percent(self):
        tax_division_100 = self.division_tax(100.0, price_include_override='tax_included')

        document = self.populate_document(self.init_document(
            lines=[{
                'price_unit': 100.0,
                'tax_ids': tax_division_100,
            }],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': 0.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax_division_100.id,
                        'base_amount_currency': 0.0,
                        'tax_amount_currency': 100.0,
                    },
                ],
            }],
            expected_base_amount=0.0,
            expected_tax_amount=100.0,
            expected_total_amount=100.0,
        )
        self._run_js_tests()

    def test_tax_reverse_charge_giving_same_results(self):
        tax = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )

        def assert_document():
            document = self.populate_document(self.init_document(
                lines=[{'price_unit': 100.0, 'tax_ids': tax}],
            ))
            self.assert_base_lines_tax_details(
                document=document,
                expected_base_lines_tax_details=[{
                    'total_excluded_currency': 100.0,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax.id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 21.0,
                        },
                        {
                            'tax_id': tax.id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': -21.0,
                        },
                    ],
                }],
                expected_base_amount=100.0,
                expected_tax_amount=0.0,
                expected_total_amount=100.0,
            )

        assert_document()
        tax.include_base_amount = True
        assert_document()
        tax.price_include_override = 'tax_included'
        assert_document()
        self._run_js_tests()

    def test_fixed_tax_price_included_affect_base_on_0(self):
        tax = self.fixed_tax(0.05, price_include_override='tax_included', include_base_amount=True)

        document = self.populate_document(self.init_document(
            lines=[{
                'price_unit': 0.0,
                'tax_ids': tax,
            }],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[{
                'total_excluded_currency': -0.05,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': -0.05,
                        'tax_amount_currency': 0.05,
                    },
                ],
            }],
            expected_base_amount=-0.05,
            expected_tax_amount=0.05,
            expected_total_amount=0.0,
        )
        self._run_js_tests()

    def test_tax_with_zero_total_base(self):
        """Check that the base line delta still is dispatched if net tax is zero."""
        tax_19_99 = self.percent_tax(19.99)
        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 19.99, 'tax_ids': tax_19_99},
                {'price_unit': 19.99, 'tax_ids': tax_19_99},
                {'price_unit': -39.98, 'tax_ids': tax_19_99},
            ],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[
                {
                    'total_excluded_currency': 19.99,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_19_99.id,
                            'base_amount_currency': 19.99,
                            'tax_amount_currency': 4.0,
                        },
                    ],
                },
                {
                    'total_excluded_currency': 19.99,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_19_99.id,
                            'base_amount_currency': 19.99,
                            'tax_amount_currency': 3.99,
                        },
                    ],
                },
                {
                    'total_excluded_currency': -39.98,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_19_99.id,
                            'base_amount_currency': -39.98,
                            'tax_amount_currency': -7.99,
                        },
                    ],
                },
            ],
            expected_base_amount=0.0,
            expected_tax_amount=0.0,
            expected_total_amount=0.0,
        )

        tax_7 = self.percent_tax(7.0)
        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 2990.4, 'tax_ids': tax_7},
                {'price_unit': 128.8, 'tax_ids': tax_7},
                {'price_unit': 128.8, 'tax_ids': tax_7},
                {'price_unit': 834.4, 'tax_ids': tax_7},
                {'price_unit': 14.0, 'tax_ids': tax_7},
                {'price_unit': -4096.4, 'tax_ids': tax_7},
            ],
        ))
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[
                {
                    'total_excluded_currency': 2990.4,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_7.id,
                            'base_amount_currency': 2990.4,
                            'tax_amount_currency': 209.33,
                        },
                    ],
                },
                {
                    'total_excluded_currency': 128.8,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_7.id,
                            'base_amount_currency': 128.8,
                            'tax_amount_currency': 9.02,
                        },
                    ],
                },
                {
                    'total_excluded_currency': 128.8,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_7.id,
                            'base_amount_currency': 128.8,
                            'tax_amount_currency': 9.02,
                        },
                    ],
                },
                {
                    'total_excluded_currency': 834.4,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_7.id,
                            'base_amount_currency': 834.4,
                            'tax_amount_currency': 58.41,
                        },
                    ],
                },
                {
                    'total_excluded_currency': 14.0,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_7.id,
                            'base_amount_currency': 14.0,
                            'tax_amount_currency': 0.97,
                        },
                    ],
                },
                {
                    'total_excluded_currency': -4096.4,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax_7.id,
                            'base_amount_currency': -4096.4,
                            'tax_amount_currency': -286.75,
                        },
                    ],
                },
            ],
            expected_base_amount=0.0,
            expected_tax_amount=0.0,
            expected_total_amount=0.0,
        )

        self._run_js_tests()

    def test_taxes_batches_1(self):
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)

        default_expected_values_base_affected = {
            'expected_base_lines_tax_details': [
                {
                    'total_excluded_currency': 99.0,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax1.id,
                            'base_amount_currency': 99.0,
                            'tax_amount_currency': 1.0,
                            'tax_ids': [tax2.id],
                        },
                        {
                            'tax_id': tax2.id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 21.0,
                            'tax_ids': [],
                        },
                    ],
                },
            ],
            'expected_base_amount': 99.0,
            'expected_tax_amount': 22.0,
            'expected_total_amount': 121.0,
        }
        default_expected_values_not_base_affected = {
            'expected_base_lines_tax_details': [
                {
                    'total_excluded_currency': 99.0,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax1.id,
                            'base_amount_currency': 99.0,
                            'tax_amount_currency': 1.0,
                            'tax_ids': [],
                        },
                        {
                            'tax_id': tax2.id,
                            'base_amount_currency': 99.0,
                            'tax_amount_currency': 20.79,
                            'tax_ids': [],
                        },
                    ],
                },
            ],
            'expected_base_amount': 99.0,
            'expected_tax_amount': 21.79,
            'expected_total_amount': 120.79,
        }

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2                                          T
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 99.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_base_affected)

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 121.0, 'tax_ids': tax1 + tax2, 'special_mode': 'total_included'}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_base_affected)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2
        tax2.is_base_affected = False

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 99.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_not_base_affected)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T                                   T
        # tax2      T                                   T
        tax1.include_base_amount = False
        tax1.price_include_override = 'tax_included'
        tax2.is_base_affected = True
        tax2.price_include_override = 'tax_included'

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 121.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_base_affected)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T               T                   T
        # tax2      T                                   T
        tax1.include_base_amount = True

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 121.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_base_affected)

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 99.0, 'tax_ids': tax1 + tax2, 'special_mode': 'total_excluded'}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_base_affected)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T               T                   T
        # tax2      T
        tax2.is_base_affected = False

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 121.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_base_affected)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T               T                   T
        # tax2
        tax2.price_include_override = 'tax_excluded'

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_not_base_affected)

        self._run_js_tests()

    def test_taxes_batches_2(self):
        tax1 = self.percent_tax(10, include_base_amount=False, price_include_override='tax_included')
        tax2 = self.percent_tax(10, include_base_amount=False, price_include_override='tax_included')

        default_expected_values_single_batch = {
            'expected_base_lines_tax_details': [
                {
                    'total_excluded_currency': 83.34,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax1.id,
                            'base_amount_currency': 83.34,
                            'tax_amount_currency': 8.33,
                            'tax_ids': [],
                        },
                        {
                            'tax_id': tax2.id,
                            'base_amount_currency': 83.34,
                            'tax_amount_currency': 8.33,
                            'tax_ids': [],
                        },
                    ],
                },
            ],
            'expected_base_amount': 83.34,
            'expected_tax_amount': 16.66,
            'expected_total_amount': 100.0,
        }
        default_expected_values_two_batches = {
            'expected_base_lines_tax_details': [
                {
                    'total_excluded_currency': 82.65,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax1.id,
                            'base_amount_currency': 82.65,
                            'tax_amount_currency': 8.26,
                            'tax_ids': [tax2.id],
                        },
                        {
                            'tax_id': tax2.id,
                            'base_amount_currency': 90.91,
                            'tax_amount_currency': 9.09,
                            'tax_ids': [],
                        },
                    ],
                },
            ],
            'expected_base_amount': 82.65,
            'expected_tax_amount': 17.35,
            'expected_total_amount': 100.0,
        }

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T                                   T
        # tax2      T                                   T
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_single_batch)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T                                   T
        # tax2      T               T                   T
        tax2.include_base_amount = True

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_two_batches)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T                                   T
        # tax2      T               T
        tax2.is_base_affected = False

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_single_batch)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T                                   T
        # tax2      T               T
        tax1.include_base_amount = True
        tax2.is_base_affected = True

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_two_batches)

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T               T                   T
        # tax2      T                                   T
        tax1.include_base_amount = True
        tax2.include_base_amount = False
        tax2.is_base_affected = True

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(document, **default_expected_values_two_batches)

        self._run_js_tests()

    def test_taxes_batches_3(self):
        """ Make sure included taxes are always evaluated first. """
        tax1 = self.percent_tax(10, include_base_amount=False, price_include_override='tax_excluded')
        tax2 = self.percent_tax(10, include_base_amount=False, price_include_override='tax_included')

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                                          T
        # tax2      T                                   T
        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(
            document,
            expected_base_lines_tax_details=[
                {
                    'total_excluded_currency': 90.91,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax2.id,
                            'base_amount_currency': 90.91,
                            'tax_amount_currency': 9.09,
                            'tax_ids': [],
                        },
                        {
                            'tax_id': tax1.id,
                            'base_amount_currency': 90.91,
                            'tax_amount_currency': 9.09,
                            'tax_ids': [],
                        },
                    ],
                },
            ],
            expected_base_amount=90.91,
            expected_tax_amount=18.18,
            expected_total_amount=109.09,
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2      T               T                   T
        tax1.include_base_amount = True
        tax2.include_base_amount = True

        document = self.populate_document(self.init_document(
            lines=[{'price_unit': 100.0, 'tax_ids': tax1 + tax2}],
        ))
        self.assert_base_lines_tax_details(
            document,
            expected_base_lines_tax_details=[
                {
                    'total_excluded_currency': 90.91,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax2.id,
                            'base_amount_currency': 90.91,
                            'tax_amount_currency': 9.09,
                            'tax_ids': [tax1.id],
                        },
                        {
                            'tax_id': tax1.id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 10.0,
                            'tax_ids': [],
                        },
                    ],
                },
            ],
            expected_base_amount=90.91,
            expected_tax_amount=19.09,
            expected_total_amount=110.0,
        )

        self._run_js_tests()

    def test_taxes_batches_4(self):
        tax1 = self.fixed_tax(1, include_base_amount=True, price_include_override='tax_included')
        tax2 = self.fixed_tax(5, include_base_amount=False, price_include_override='tax_included')
        tax3 = self.percent_tax(21, include_base_amount=False, price_include_override='tax_included')
        taxes = tax1 + tax2 + tax3

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 21.53, 'tax_ids': taxes},
                {'price_unit': 21.53, 'tax_ids': taxes},
            ],
        ))
        expected_base_line_tax_details_values_common = {
            'total_excluded_currency': 11.80,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'tax_amount_currency': 1.0,
                },
                {
                    'tax_id': tax2.id,
                    'tax_amount_currency': 5.0,
                },
                {
                    'tax_id': tax3.id,
                },
            ],
        }
        expected_base_line_tax_details_values_1 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded_currency': -0.01,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 11.79,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][1],
                    'base_amount_currency': 12.79,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                    'base_amount_currency': 17.79,
                    'tax_amount_currency': 3.74,
                },
            ],
        }
        expected_base_line_tax_details_values_2 = {
            **expected_base_line_tax_details_values_common,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][0],
                    'base_amount_currency': 11.8,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][1],
                    'base_amount_currency': 12.8,
                },
                {
                    **expected_base_line_tax_details_values_common['taxes_data'][2],
                    'base_amount_currency': 17.80,
                    'tax_amount_currency': 3.73,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values_1, expected_base_line_tax_details_values_2],
            expected_base_amount=23.59,
            expected_tax_amount=19.47,
            expected_total_amount=43.06,
        )

        self._run_js_tests()


    def test_reverse_charge_division_tax(self):
        tax = self.division_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )

        expected_values = {
            'expected_base_lines_tax_details': [{
                'total_excluded_currency': 79.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 79.0,
                        'tax_amount_currency': 28.6,
                    },
                    {
                        'tax_id': tax.id,
                        'base_amount_currency': 79.0,
                        'tax_amount_currency': -28.6,
                    },
                ],
            }],
            'expected_base_amount': 79.0,
            'expected_tax_amount': 0.0,
            'expected_total_amount': 79.0,
        }

        document = self.populate_document(self.init_document([
            {'price_unit': 79.0, 'tax_ids': tax},
        ]))
        self.assert_base_lines_tax_details(document, **expected_values)

        tax.price_include_override = 'tax_included'
        document = self.populate_document(self.init_document([
            {'price_unit': 79.0, 'tax_ids': tax},
        ]))
        self.assert_base_lines_tax_details(document, **expected_values)

        self._run_js_tests()

    def test_adapt_price_unit_to_another_taxes(self):
        tax_fixed_incl = self.fixed_tax(10, price_include_override='tax_included')
        tax_fixed_excl = self.fixed_tax(10, price_include_override='tax_excluded')
        tax_include_src = self.percent_tax(21, price_include_override='tax_included')
        tax_include_dst = self.percent_tax(6, price_include_override='tax_included')
        tax_exclude_src = self.percent_tax(15, price_include_override='tax_excluded')
        tax_exclude_dst = self.percent_tax(21, price_include_override='tax_excluded')

        self.assert_adapt_price_unit_to_another_taxes(
            121.0,
            tax_include_src,
            tax_include_dst,
            106.0,
        )
        self.assert_adapt_price_unit_to_another_taxes(
            100.0,
            tax_exclude_src,
            tax_include_dst,
            100.0,
        )
        self.assert_adapt_price_unit_to_another_taxes(
            121.0,
            tax_include_src,
            tax_exclude_dst,
            100.0,
        )
        self.assert_adapt_price_unit_to_another_taxes(
            100.0,
            tax_exclude_src,
            tax_exclude_dst,
            100.0,
        )
        self.assert_adapt_price_unit_to_another_taxes(
            100.0,
            tax_fixed_incl + tax_exclude_src,
            tax_fixed_incl + tax_include_dst,
            100.0,
        )
        self.assert_adapt_price_unit_to_another_taxes(
            100.0,
            tax_fixed_excl + tax_include_src,
            tax_fixed_excl + tax_exclude_dst,
            100.0,
        )

        tax_fixed_incl.include_base_amount = True
        tax_fixed_excl.include_base_amount = True

        self.assert_adapt_price_unit_to_another_taxes(
            133.1,
            tax_fixed_incl + tax_include_src,
            tax_fixed_excl + tax_exclude_dst,
            100.0,
        )

        self._run_js_tests()

    def test_global_discount_100_percent_cash_rounding_up(self):
        """A 100% discount + round-up cash rounding must keep the total at 0: the base + tax
        residue left by the discount must not be inflated into a full rounding step."""
        tax = self.percent_tax(17)
        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 11.752137, 'tax_ids': tax},
                {'price_unit': 21.367521, 'tax_ids': tax},
            ],
            cash_rounding=self.cash_rounding_a,  # add_invoice_line, rounding 0.05, method 'UP'
        ))
        self.assert_global_discount_base_lines_tax_details(
            document=document,
            amount_type='percent',
            amount=100,
            expected_base_lines_tax_details=None,
            expected_base_amount=0.0,
            expected_tax_amount=0.0,
            expected_total_amount=0.0,
        )

        self._run_js_tests()

    def test_down_payment_taxes_fixed_tax_last_position(self):
        tax1 = self.percent_tax(20)
        tax2 = self.fixed_tax(10)
        taxes = tax1 + tax2

        document_params = self.init_document(lines=[{'price_unit': 100.0, 'tax_ids': taxes}])
        document = self.populate_document(document_params)

        self.assert_down_payment_base_lines_tax_details(
            document=document,
            amount_type='percent',
            amount=50.0,
            expected_base_lines_tax_details=None,
            expected_base_amount=50.0,
            expected_tax_amount=10.0,
            expected_total_amount=60.0,
        )

        tax2.include_base_amount = True

        self.assert_down_payment_base_lines_tax_details(
            document=document,
            amount_type='percent',
            amount=50.0,
            expected_base_lines_tax_details=None,
            expected_base_amount=50.0,
            expected_tax_amount=10.0,
            expected_total_amount=60.0,
        )

        self._run_js_tests()

    def test_down_payment_no_tax(self):
        document_params = self.init_document(lines=[
            {'price_unit': 35.0},
            {'price_unit': -5.0},
            {'price_unit': 30.0},
            {'price_unit': 15.0},
            {'price_unit': 15.0},
        ])
        document = self.populate_document(document_params)

        self.assert_down_payment_base_lines_tax_details(
            document=document,
            amount_type='percent',
            amount=50.0,
            expected_base_lines_tax_details=None,
            expected_base_amount=45.0,
            expected_tax_amount=0.0,
            expected_total_amount=45.0,
        )

        self._run_js_tests()

    def test_down_payment_fixed_amount_reverse_charge_tax(self):
        tax = self.percent_tax(
            21,
            invoice_repartition_line_ids=[
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'repartition_type': 'tax'}),
                Command.create({'factor_percent': -100, 'repartition_type': 'tax'}),
            ],
            refund_repartition_line_ids=[
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'repartition_type': 'tax'}),
                Command.create({'factor_percent': -100, 'repartition_type': 'tax'}),
            ],
        )

        document_params = self.init_document(lines=[{'price_unit': 12.0, 'tax_ids': tax}])
        document = self.populate_document(document_params)

        self.assert_down_payment_base_lines_tax_details(
            document=document,
            amount_type='fixed',
            amount=3.0,
            expected_base_lines_tax_details=[
                {
                    'total_excluded_currency': 3.0,
                    'delta_total_excluded_currency': 0.0,
                    'taxes_data': [
                        {
                            'tax_id': tax.id,
                            'tax_amount_currency': 0.63,
                            'base_amount_currency': 3.0,
                        },
                        {
                            'tax_id': tax.id,
                            'tax_amount_currency': -0.63,
                            'base_amount_currency': 3.0,
                        },
                    ],
                }
            ],
            expected_base_amount=3.0,
            expected_tax_amount=0.0,
            expected_total_amount=3.0,
        )
        self._run_js_tests()

    def test_include_base_amount_in_aggregate_base_line_tax_details(self):
        """ Test that the tax amount from a tax that is affecting the base of subsequent taxes
        is correctly propagated in '_aggregate_base_line_tax_details'
        """
        AccountTax = self.env['account.tax']
        tax_20 = self.percent_tax(20, include_base_amount=True)
        tax_18 = self.percent_tax(18)
        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 2000.0, 'quantity': 5, 'discount': 20.0, 'tax_ids': tax_20 + tax_18},
            ],
        ))
        AccountTax._add_tax_details(document['lines'], self.env.company)

        def tax_grouping_function(base_line, tax_data):
            if not tax_data:
                return None
            return {
                'amount': tax_data['tax'].amount,
            }

        aggregated_data = AccountTax._aggregate_base_line_tax_details(document['lines'][0], tax_grouping_function)
        expected_values = [{
            'base_amount': 8000.0,
            'base_amount_currency': 8000.0,
            'raw_base_amount': 8000.0,
            'raw_base_amount_currency': 8000.0,
            'raw_tax_amount': 1600.0,
            'raw_tax_amount_currency': 1600.0,
            'raw_total_excluded': 8000.0,
            'raw_total_excluded_currency': 8000.0,
            'target_base_amount': 8000.0,
            'target_base_amount_currency': 8000.0,
            'target_tax_amount': 1600.0,
            'target_tax_amount_currency': 1600.0,
            'target_total_excluded': 8000.0,
            'target_total_excluded_currency': 8000.0,
            'tax_amount': 1600.0,
            'tax_amount_currency': 1600.0,
            'total_excluded': 8000.0,
            'total_excluded_currency': 8000.0,
        }, {
            'base_amount': 9600.0,
            'base_amount_currency': 9600.0,
            'raw_base_amount': 9600.0,
            'raw_base_amount_currency': 9600.0,
            'raw_tax_amount': 1728.0,
            'raw_tax_amount_currency': 1728.0,
            'raw_total_excluded': 9600.0,
            'raw_total_excluded_currency': 9600.0,
            'target_base_amount': 9600.0,
            'target_base_amount_currency': 9600.0,
            'target_tax_amount': 1728.0,
            'target_tax_amount_currency': 1728.0,
            'target_total_excluded': 9600.0,
            'target_total_excluded_currency': 9600.0,
            'tax_amount': 1728.0,
            'tax_amount_currency': 1728.0,
            'total_excluded': 9600.0,
            'total_excluded_currency': 9600.0,
        }]
        for i, data in enumerate(aggregated_data.values()):
            for key in ('grouping_key', 'taxes_data'):
                data.pop(key)
            self.assertDictEqual(expected_values[i], data)
