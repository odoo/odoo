from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputation(TestTaxCommon):

    def test_taxes_ordering(self):
        tax_division = self.division_tax(10.0, sequence=1)
        tax_fixed = self.fixed_tax(10.0, sequence=2)
        tax_percent = self.percent_tax(10.0, sequence=3)
        tax_group = self.group_of_taxes(tax_fixed + tax_percent, sequence=4)

        self.assert_taxes_computation(
            tax_group | tax_division,
            200.0,
            {
                'total_included': 252.22,
                'total_excluded': 200.0,
                'taxes_data': (
                    (200.0, 22.22),
                    (200.0, 10.0),
                    (200.0, 20.0),
                ),
            },
        )

        tax_percent1 = self.percent_tax(0.0, price_include_override='tax_included')
        tax_percent2 = self.percent_tax(8.0, price_include_override='tax_included')
        tax_group1 = self.group_of_taxes(tax_percent1, sequence=5)
        tax_group2 = self.group_of_taxes(tax_percent2, sequence=6)
        self.assert_taxes_computation(
            tax_group1 | tax_group2,
            124.4,
            {
                'total_included': 124.4,
                'total_excluded': 115.19,
                'taxes_data': (
                    (115.19, 0.0),
                    (115.19, 9.21),
                ),
            },
        )
        self._run_js_tests()

    def test_random_case_1(self):
        tax_percent_8_price_included = self.percent_tax(8.0, price_include_override='tax_included')
        tax_percent_0_price_included = self.percent_tax(0.0, price_include_override='tax_included')

        self.assert_taxes_computation(
            tax_percent_8_price_included + tax_percent_0_price_included,
            124.40,
            {
                'total_included': 124.40,
                'total_excluded': 115.19,
                'taxes_data': (
                    (115.19, 9.21),
                    (115.19, 0.0),
                ),
            },
            rounding_method='round_per_line',
        )
        self.assert_taxes_computation(
            tax_percent_8_price_included + tax_percent_0_price_included,
            124.40,
            {
                'total_included': 124.40,
                'total_excluded': 115.185185,
                'taxes_data': (
                    (115.185185, 9.214815),
                    (115.185185, 0.0),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_random_case_2(self):
        tax_percent_5_price_included = self.percent_tax(5.0, price_include_override='tax_included')
        currency_dp_half = 0.05

        self.assert_taxes_computation(
            tax_percent_5_price_included,
            5.0,
            {
                'total_included': 5.0,
                'total_excluded': 4.75,
                'taxes_data': (
                    (4.75, 0.25),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_half,
        )
        self.assert_taxes_computation(
            tax_percent_5_price_included,
            10.0,
            {
                'total_included': 10.0,
                'total_excluded': 9.5,
                'taxes_data': (
                    (9.5, 0.5),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_half,
        )
        self.assert_taxes_computation(
            tax_percent_5_price_included,
            50.0,
            {
                'total_included': 50.0,
                'total_excluded': 47.6,
                'taxes_data': (
                    (47.6, 2.4),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_half,
        )
        self.assert_taxes_computation(
            tax_percent_5_price_included,
            5.0,
            {
                'total_included': 5.0,
                'total_excluded': 4.761905,
                'taxes_data': (
                    (4.761905, 0.238095),
                ),
            },
            rounding_method='round_globally',
        )
        self.assert_taxes_computation(
            tax_percent_5_price_included,
            10.0,
            {
                'total_included': 10.0,
                'total_excluded': 9.52381,
                'taxes_data': (
                    (9.52381, 0.47619),
                ),
            },
            rounding_method='round_globally',
        )
        self.assert_taxes_computation(
            tax_percent_5_price_included,
            50.0,
            {
                'total_included': 50.0,
                'total_excluded': 47.619048,
                'taxes_data': (
                    (47.619048, 2.380952),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_random_case_3(self):
        tax_percent_15_price_excluded = self.percent_tax(15.0)
        tax_percent_5_5_price_included = self.percent_tax(5.5, price_include_override='tax_included')

        self.assert_taxes_computation(
            tax_percent_15_price_excluded + tax_percent_5_5_price_included,
            2300.0,
            {
                'total_included': 2627.01,
                'total_excluded': 2180.09,
                'taxes_data': (
                    (2180.09, 327.01),
                    (2180.09, 119.91),
                ),
            },
            rounding_method='round_per_line',
        )
        self.assert_taxes_computation(
            tax_percent_15_price_excluded + tax_percent_5_5_price_included,
            2300.0,
            {
                'total_included': 2627.014218,
                'total_excluded': 2180.094787,
                'taxes_data': (
                    (2180.094787, 327.014218),
                    (2180.094787, 119.905213),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_random_case_4(self):
        tax_percent_12_price_included = self.percent_tax(12.0, price_include_override='tax_included')

        self.assert_taxes_computation(
            tax_percent_12_price_included,
            52.50,
            {
                'total_included': 52.50,
                'total_excluded': 46.87,
                'taxes_data': (
                    (46.87, 5.63),
                ),
            },
            rounding_method='round_per_line',
        )
        self.assert_taxes_computation(
            tax_percent_12_price_included,
            52.50,
            {
                'total_included': 52.50,
                'total_excluded': 46.875,
                'taxes_data': (
                    (46.875, 5.625),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_random_case_5(self):
        tax_percent_19 = self.percent_tax(19.0)
        tax_percent_19_price_included = self.percent_tax(19.0, price_include_override='tax_included')
        currency_dp_0 = 1.0

        self.assert_taxes_computation(
            tax_percent_19,
            22689.0,
            {
                'total_included': 27000.0,
                'total_excluded': 22689.0,
                'taxes_data': (
                    (22689, 4311),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_0,
        )
        self.assert_taxes_computation(
            tax_percent_19,
            9176.0,
            {
                'total_included': 10919.0,
                'total_excluded': 9176.0,
                'taxes_data': (
                    (9176, 1743),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_0,
        )
        self.assert_taxes_computation(
            tax_percent_19_price_included,
            27000.0,
            {
                'total_included': 27000.0,
                'total_excluded': 22689.0,
                'taxes_data': (
                    (22689.0, 4311.0),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_0,
        )
        self.assert_taxes_computation(
            tax_percent_19_price_included,
            10920.0,
            {
                'total_included': 10920.0,
                'total_excluded': 9176.0,
                'taxes_data': (
                    (9176.0, 1744.0),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_0,
        )
        self.assert_taxes_computation(
            tax_percent_19,
            22689.0,
            {
                'total_included': 26999.91,
                'total_excluded': 22689.0,
                'taxes_data': (
                    (22689, 4310.91),
                ),
            },
            rounding_method='round_globally',
        )
        self.assert_taxes_computation(
            tax_percent_19,
            9176.0,
            {
                'total_included': 10919.44,
                'total_excluded': 9176.0,
                'taxes_data': (
                    (9176, 1743.44),
                ),
            },
            rounding_method='round_globally',
        )
        self.assert_taxes_computation(
            tax_percent_19_price_included,
            27000.0,
            {
                'total_included': 27000.0,
                'total_excluded': 22689.07563,
                'taxes_data': (
                    (22689.07563, 4310.92437),
                ),
            },
            rounding_method='round_globally',
        )
        self.assert_taxes_computation(
            tax_percent_19_price_included,
            10920.0,
            {
                'total_included': 10920.0,
                'total_excluded': 9176.470588,
                'taxes_data': (
                    (9176.470588, 1743.529412),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_random_case_6(self):
        tax_percent_20_price_included = self.percent_tax(20.0, price_include_override='tax_included')
        currency_dp_6 = 0.000001

        self.assert_taxes_computation(
            tax_percent_20_price_included,
            399.999999,
            {
                'total_included': 399.999999,
                'total_excluded': 333.333332,
                'taxes_data': (
                    # 399.999999 / 1.20 * 0.20 ~= 66.666667
                    # 399.999999 - 66.666667 = 333.333332
                    (333.333332, 66.666667),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_6,
        )
        self.assert_taxes_computation(
            tax_percent_20_price_included,
            399.999999,
            {
                'total_included': 399.999999,
                'total_excluded': 333.3333325,
                'taxes_data': (
                    (333.3333325, 66.6666665),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_random_case_7(self):
        tax_percent_21_price_included = self.percent_tax(21.0, price_include_override='tax_included')
        currency_dp_6 = 0.000001

        self.assert_taxes_computation(
            tax_percent_21_price_included,
            11.90,
            {
                'total_included': 11.90,
                'total_excluded': 9.83,
                'taxes_data': (
                    (9.83, 2.07),
                ),
            },
            rounding_method='round_per_line',
        )
        self.assert_taxes_computation(
            tax_percent_21_price_included,
            2.80,
            {
                'total_included': 2.80,
                'total_excluded': 2.31,
                'taxes_data': (
                    (2.31, 0.49),
                ),
            },
            rounding_method='round_per_line',
        )
        self.assert_taxes_computation(
            tax_percent_21_price_included,
            7.0,
            {
                'total_included': 7.0,
                'total_excluded': 5.785124,
                'taxes_data': (
                    (5.785124, 1.214876),
                ),
            },
            rounding_method='round_per_line',
            precision_rounding=currency_dp_6,
        )
        self.assert_taxes_computation(
            tax_percent_21_price_included,
            11.90,
            {
                'total_included': 11.90,
                'total_excluded': 9.834711,
                'taxes_data': (
                    (9.834711, 2.065289),
                ),
            },
            rounding_method='round_globally',
        )
        self.assert_taxes_computation(
            tax_percent_21_price_included,
            2.80,
            {
                'total_included': 2.80,
                'total_excluded': 2.31405,
                'taxes_data': (
                    (2.31405, 0.48595),
                ),
            },
            rounding_method='round_globally',
        )
        self.assert_taxes_computation(
            tax_percent_21_price_included,
            7.0,
            {
                'total_included': 7.0,
                'total_excluded': 5.785124,
                'taxes_data': (
                    (5.785124, 1.214876),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_random_case_8(self):
        tax_percent_20_withholding = self.percent_tax(-20.0)
        tax_percent_4 = self.percent_tax(4.0, include_base_amount=True)
        tax_percent_22 = self.percent_tax(22.0)
        taxes = tax_percent_20_withholding + tax_percent_4 + tax_percent_22

        self.assert_taxes_computation(
            taxes,
            50.0,
            {
                'total_included': 53.44,
                'total_excluded': 50.0,
                'taxes_data': (
                    (50.0, -10.0),
                    (50.0, 2.0),
                    (52.0, 11.44),
                ),
            },
        )
        self._run_js_tests()

    def test_random_case_9(self):
        tax_division_100 = self.division_tax(100.0, price_include_override='tax_included')

        self.assert_taxes_computation(
            tax_division_100,
            100.0,
            {
                'total_included': 100.0,
                'total_excluded': 0.0,
                'taxes_data': (
                    (0.0, 100.0),
                ),
            },
        )
        self._run_js_tests()

    def test_fixed_tax_price_included_affect_base_on_0(self):
        tax = self.fixed_tax(0.05, price_include_override='tax_included', include_base_amount=True)
        self.assert_taxes_computation(
            tax,
            0.0,
            {
                'total_included': 0.0,
                'total_excluded': -0.05,
                'taxes_data': (
                    (-0.05, 0.05),
                ),
            },
        )
        self._run_js_tests()

    def test_percent_taxes_for_l10n_in(self):
        tax1 = self.percent_tax(6)
        tax2 = self.percent_tax(6)
        tax3 = self.percent_tax(3)

        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            100.0,
            {
                'total_included': 115.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (100.0, 3.0),
                ),
            },
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2                                          T
        # tax3                                          T
        tax1.include_base_amount = True
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            100.0,
            {
                'total_included': 115.54,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 6.0),
                    (106.0, 6.36),
                    (106.0, 3.18),
                ),
            },
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2                      T                   T
        # tax3                                          T
        tax2.include_base_amount = True
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            100.0,
            {
                'total_included': 115.7308,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 6.0),
                    (106.0, 6.36),
                    (112.36, 3.3708),
                ),
            },
            rounding_method='round_globally',
            excluded_special_modes=['total_included'],  # Impossible.
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2                      T
        # tax3                                          T
        tax2.is_base_affected = False
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            100.0,
            {
                'total_included': 115.36,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (112.0, 3.36),
                ),
            },
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T               T                   T
        # tax2      T               T
        # tax3                                          T
        tax1.price_include_override = 'tax_included'
        tax2.price_include_override = 'tax_included'
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            112.0,
            {
                'total_included': 115.36,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (112.0, 3.36),
                ),
            },
            rounding_method='round_globally',
        )

        # Ensure tax1 & tax2 give always the same result.
        self.assert_taxes_computation(
            tax1 + tax2,
            17.79,
            {
                'total_included': 17.79,
                'total_excluded': 15.883929,
                'taxes_data': (
                    (15.883929, 0.953036),
                    (15.883929, 0.953036),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_division_taxes_for_l10n_br(self):
        tax1 = self.division_tax(5)
        tax2 = self.division_tax(3)
        tax3 = self.division_tax(0.65)
        tax4 = self.division_tax(9)
        tax5 = self.division_tax(15)

        # Same of tax4/tax5 except the amount is based on 32% of the base amount.
        self.assert_taxes_computation(
            tax1 + tax2 + tax3 + tax4 + tax5,
            32.33,
            {
                'total_included': 48.00297,
                'total_excluded': 32.33,
                'taxes_data': (
                    (32.33, 2.400148),
                    (32.33, 1.440089),
                    (32.33, 0.312019),
                    (32.33, 4.320267),
                    (32.33, 7.200445),
                ),
            },
            rounding_method='round_globally',
        )

        (tax1 + tax2 + tax3 + tax4 + tax5).price_include_override = 'tax_included'
        self.assert_taxes_computation(
            tax1 + tax2 + tax3 + tax4 + tax5,
            48.0,
            {
                'total_included': 48.0,
                'total_excluded': 32.328,
                'taxes_data': (
                    (32.328, 2.4),
                    (32.328, 1.44),
                    (32.328, 0.312),
                    (32.328, 4.32),
                    (32.328, 7.2),
                ),
            },
            rounding_method='round_globally',
        )
        self._run_js_tests()

    def test_fixed_taxes_for_l10n_be(self):
        tax1 = self.fixed_tax(1)
        tax2 = self.percent_tax(21)
        tax3 = self.fixed_tax(2)

        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            20.0,
            {
                'total_included': 136.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 5.0),
                    (100.0, 21.0),
                    (100.0, 10.0),
                ),
            },
            quantity=5,
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1                      T
        # tax2
        # tax3
        tax1.include_base_amount = True
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            19.0,
            {
                'total_included': 131.0,
                'total_excluded': 95.0,
                'taxes_data': (
                    (95.0, 5.0),
                    (100.0, 21.0),
                    (100.0, 10.0),
                ),
            },
            quantity=5,
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1                      T
        # tax2      T
        # tax3
        tax2.price_include_override = 'tax_included'
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            120.0,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'taxes_data': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1                      T
        # tax2      T               T
        # tax3
        tax2.include_base_amount = True
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            120.0,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'taxes_data': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1
        # tax2      T               T
        # tax3
        tax1.include_base_amount = False
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            121.0,
            {
                'total_included': 124.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1
        # tax2                      T
        # tax3
        tax2.price_include_override = 'tax_excluded'
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            100.0,
            {
                'total_included': 124.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            rounding_method='round_globally'
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1      T
        # tax2      T               T
        # tax3
        tax1.price_include_override = 'tax_included'
        tax2.price_include_override = 'tax_included'
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            122.0,
            {
                'total_included': 124.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 1.0),
                    (100.0, 21.0),
                    (122.0, 2.0),
                ),
            },
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1      T
        # tax2      T
        # tax3
        tax2.include_base_amount = False
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            122.0,
            {
                'total_included': 124.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 1.0),
                    (100.0, 21.0),
                    (122.0, 2.0),
                ),
            },
            rounding_method='round_globally',
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1      T               T
        # tax2      T               T
        # tax3
        tax1.include_base_amount = True
        tax2.include_base_amount = True
        self.assert_taxes_computation(
            tax1 + tax2 + tax3,
            121.0,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'taxes_data': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            rounding_method='round_globally',
        )
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
        self._run_js_tests()
