# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class AccountTestBusinessTaxesComputation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.current_assets_type = cls.env.ref('account.data_account_type_current_assets')

        cls.account_1 = cls.env['account.account'].create({
            'name': 'account_1',
            'code': 'account_1',
            'user_type_id': cls.current_assets_type.id,
        })
        cls.account_2 = cls.env['account.account'].create({
            'name': 'account_2',
            'code': 'account_2',
            'user_type_id': cls.current_assets_type.id,
        })

        cls.percent_tax_10_with_rep = cls.env['account.tax'].create({
            'name': 'percent_tax_10_with_rep',
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 10,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'account_id': cls.account_1.id, 'factor_percent': 30.0}),
                (0, 0, {'repartition_type': 'tax', 'account_id': cls.account_2.id, 'factor_percent': 70.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'account_id': cls.account_1.id, 'factor_percent': 30.0}),
                (0, 0, {'repartition_type': 'tax', 'account_id': cls.account_2.id, 'factor_percent': 70.0}),
            ],
        })
        cls.percent_tax_20_price_incl = cls.env['account.tax'].create({
            'name': 'percent_tax_20_price_incl',
            'amount_type': 'percent',
            'amount': 20,
            'sequence': 20,
            'price_include': True,
            'include_base_amount': False,
        })
        cls.percent_tax_30 = cls.env['account.tax'].create({
            'name': 'percent_tax_30',
            'amount_type': 'percent',
            'amount': 30,
            'sequence': 30,
        })
        cls.group_of_taxes_20_then_30 = cls.env['account.tax'].create({
            'name': 'group_of_taxes_20_then_30',
            'amount': 0.0,
            'amount_type': 'group',
            'children_tax_ids': [
                (4, cls.percent_tax_20_price_incl.id),
                (4, cls.percent_tax_30.id),
            ],
        })
        cls.percent_tax_40_price_incl_affect_base = cls.env['account.tax'].create({
            'name': 'percent_tax_40_price_incl_affect_base',
            'amount_type': 'percent',
            'amount': 40,
            'sequence': 40,
            'price_include': True,
            'include_base_amount': True,
        })
        cls.percent_tax_50 = cls.env['account.tax'].create({
            'name': 'percent_tax_50',
            'amount_type': 'percent',
            'amount': 50,
            'sequence': 50,
        })
        cls.group_of_taxes_40_then_50 = cls.env['account.tax'].create({
            'name': 'group_of_taxes_40_then_50',
            'amount': 0.0,
            'amount_type': 'group',
            'children_tax_ids': [
                (4, cls.percent_tax_40_price_incl_affect_base.id),
                (4, cls.percent_tax_50.id),
            ],
        })

    def run(self, result=None):
        # OVERRIDE
        # When overridden, all tests are run two times: one for the parent class and one for the child class.
        # However, running tests in 'AccountTestBusinessTaxesComputation' without business object doesn't make sense.
        # Then, this hack is there to ensure the tests are run only once in the child class.
        if self.__class__ == AccountTestBusinessTaxesComputation:
            return
        return super().run(result=result)

    @classmethod
    def _create_business_object(self, line_vals):
        return None

    @classmethod
    def _get_totals(cls, business_object):
        return {}

    def assertTaxesComputation(self, line_vals, expected_amount_untaxed, expected_amount_tax):
        business_object = self._create_business_object(line_vals)
        totals = self._get_totals(business_object)

        self.assertAlmostEqual(totals.get('amount_untaxed', 0.0), expected_amount_untaxed)
        self.assertAlmostEqual(totals.get('amount_tax', 0.0), expected_amount_tax)

    def test_multi_taxes_friendly_amounts(self):
        '''Test the computation of taxes on very friendly amounts ensuring no decimals.
        line 1          1000.0 * 0.10 = 100.0
        line 2          (2400.0 - (2400.0 / 1.20)) + (2000.0 * 0.30) = 400.0 + 600.0 = 1000.0
        line 3          (2800.0 - (2800.0 / 1.40)) + (2800.0 * 0.50) = 800.0 + 1400.0 = 2200.0

        amount_untaxed  1000.0 + 2000.0 + 2000.0 = 5000.0
        amount_tax      100.0 + 1000.0 + 2200.0 = 3300.0
        '''
        self.assertTaxesComputation([
            {'price_unit': 1000.0, 'tax_ids': self.percent_tax_10_with_rep.ids},
            {'price_unit': 2400.0, 'tax_ids': self.group_of_taxes_20_then_30.ids},
            {'price_unit': 2800.0, 'tax_ids': self.group_of_taxes_40_then_50.ids},
        ], 5000.0, 3300.0)

    def test_multi_taxes_with_decimals_round_per_line(self):
        '''Test the computation of taxes with decimals using the 'round_per_line' method.
        line 1          123.53 * 0.50 ~= 61.77
        line 2          678.93 * 0.50 ~= 339.47
        line 3          234.56 - (234.56 / 1.20) ~= 39.09

        amount_untaxed  123.54 + 678.94 + 195.47 = 997.95
        amount_tax      61.77 + 339.47 + 39.09 = 440.33
        '''
        self.env.company.tax_calculation_rounding_method = 'round_per_line'
        self.assertTaxesComputation([
            {'price_unit': 123.53, 'tax_ids': self.percent_tax_50.ids},
            {'price_unit': 678.93, 'tax_ids': self.percent_tax_50.ids},
            {'price_unit': 234.56, 'tax_ids': self.percent_tax_20_price_incl.ids},
        ], 997.93, 440.33)

    def test_multi_taxes_with_decimals_round_globally_1(self):
        '''Test the computation of taxes with decimals using the 'round_globally' method.
        Some tax amounts will be aggregated together.

        line 1          123.53 * 0.50 = 61.765
        line 2          678.93 * 0.50 = 339.465
        line 3          234.56 - (234.56 / 1.20) = 39.0933

        amount_untaxed  123.54 + 678.94 + 195.47 = 997.95
        amount_tax      ROUND(61.765 + 339.465) + ROUND(39.0933) = 401.23 + 39.09 = 440.32
        '''
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        self.assertTaxesComputation([
            {'price_unit': 123.53, 'tax_ids': self.percent_tax_50.ids},
            {'price_unit': 678.93, 'tax_ids': self.percent_tax_50.ids},
            {'price_unit': 234.56, 'tax_ids': self.percent_tax_20_price_incl.ids},
        ], 997.93, 440.32)

    def test_multi_taxes_with_decimals_round_globally_2(self):
        '''Test the computation of taxes with decimals using the 'round_globally' method.
        The tax amounts shouldn't be aggregated together because the taxes are not the same.

        line 1          61.62 * 0.10 = 6.162
        line 2          234.56 - (234.56 / 1.20) = 39.0933

        amount_untaxed  61.62 + 195.47 = 257.09
        amount_tax      ROUND(6.162) + ROUND(39.0933) = 6.16 + 39.09 = 45.25
        '''
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        self.assertTaxesComputation([
            {'price_unit': 61.62, 'tax_ids': self.percent_tax_10_with_rep.ids},
            {'price_unit': 234.56, 'tax_ids': self.percent_tax_20_price_incl.ids},
        ], 257.09, 45.25)
