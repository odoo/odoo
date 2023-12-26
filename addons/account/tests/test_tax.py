# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


class TestTaxCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Setup another company having a rounding of 1.0.
        cls.currency_data['currency'].rounding = 1.0
        cls.currency_no_decimal = cls.currency_data['currency']
        cls.company_data_2 = cls.setup_company_data('company_2', currency_id=cls.currency_no_decimal.id)

        cls.currency_5_round = cls.env['res.currency'].create({
            'name': 'Platinum Coin',
            'symbol': 'P$',
            'rounding': 0.05,
            'position': 'after',
            'currency_unit_label': 'Platinum',
            'currency_subunit_label': 'Palladium',
        })
        cls.company_data_3 = cls.setup_company_data('company_3', currency_id=cls.currency_5_round.id)
        cls.env.user.company_id = cls.company_data['company']

        cls.fixed_tax = cls.env['account.tax'].create({
            'name': "Fixed tax",
            'amount_type': 'fixed',
            'amount': 10,
            'sequence': 1,
        })
        cls.fixed_tax_bis = cls.env['account.tax'].create({
            'name': "Fixed tax bis",
            'amount_type': 'fixed',
            'amount': 15,
            'sequence': 2,
        })
        cls.percent_tax = cls.env['account.tax'].create({
            'name': "Percent tax",
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 3,
        })
        cls.percent_tax_bis = cls.env['account.tax'].create({
            'name': "Percent tax bis",
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 4,
        })
        cls.division_tax = cls.env['account.tax'].create({
            'name': "Division tax",
            'amount_type': 'division',
            'amount': 10,
            'sequence': 4,
        })
        cls.group_tax = cls.env['account.tax'].create({
            'name': "Group tax",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 5,
            'children_tax_ids': [
                (4, cls.fixed_tax.id, 0),
                (4, cls.percent_tax.id, 0)
            ]
        })
        cls.group_tax_bis = cls.env['account.tax'].create({
            'name': "Group tax bis",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 6,
            'children_tax_ids': [
                (4, cls.fixed_tax.id, 0),
                (4, cls.percent_tax.id, 0)
            ]
        })
        cls.group_tax_percent = cls.env['account.tax'].create({
            'name': "Group tax percent",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 6,
            'children_tax_ids': [
                (4, cls.percent_tax.id, 0),
                (4, cls.percent_tax_bis.id, 0)
            ]
        })
        cls.group_of_group_tax = cls.env['account.tax'].create({
            'name': "Group of group tax",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 7,
            'children_tax_ids': [
                (4, cls.group_tax.id, 0),
                (4, cls.group_tax_bis.id, 0)
            ]
        })
        cls.tax_with_no_account = cls.env['account.tax'].create({
            'name': "Tax with no account",
            'amount_type': 'fixed',
            'amount': 0,
            'sequence': 8,
        })
        some_account = cls.env['account.account'].search([], limit=1)
        cls.tax_with_account = cls.env['account.tax'].create({
            'name': "Tax with account",
            'amount_type': 'fixed',
            'amount': 0,
            'sequence': 8,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': some_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': some_account.id,
                }),
            ],
        })

        cls.tax_0_percent = cls.env['account.tax'].with_company(cls.company_data['company']).create({
            'name': "test_0_percent",
            'amount_type': 'percent',
            'amount': 0,
        })

        cls.tax_5_percent = cls.env['account.tax'].with_company(cls.company_data_3['company']).create({
            'name': "test_5_percent",
            'amount_type': 'percent',
            'amount': 5,
        })

        cls.tax_8_percent = cls.env['account.tax'].with_company(cls.company_data['company']).create({
            'name': "test_8_percent",
            'amount_type': 'percent',
            'amount': 8,
        })
        cls.tax_12_percent = cls.env['account.tax'].with_company(cls.company_data['company']).create({
            'name': "test_12_percent",
            'amount_type': 'percent',
            'amount': 12,
        })

        cls.tax_19_percent = cls.env['account.tax'].with_company(cls.company_data_2['company']).create({
            'name': "test_19_percent",
            'amount_type': 'percent',
            'amount': 19,
        })

        cls.tax_21_percent = cls.env['account.tax'].with_company(cls.company_data['company']).create({
            'name': "test_21_percent",
            'amount_type': 'percent',
            'amount': 19,
        })

        cls.tax_21_percent = cls.env['account.tax'].with_company(cls.company_data['company']).create({
            'name': "test_rounding_methods_2",
            'amount_type': 'percent',
            'amount': 21,
        })

        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.bank_account = cls.bank_journal.default_account_id
        cls.expense_account = cls.company_data['default_account_expense']

    def _check_compute_all_results(self, total_included, total_excluded, taxes, res):
        self.assertAlmostEqual(res['total_included'], total_included)
        self.assertAlmostEqual(res['total_excluded'], total_excluded)
        for i in range(0, len(taxes)):
            self.assertAlmostEqual(res['taxes'][i]['base'], taxes[i][0])
            self.assertAlmostEqual(res['taxes'][i]['amount'], taxes[i][1])


@tagged('post_install', '-at_install')
class TestTax(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super(TestTax, cls).setUpClass()

    def test_tax_group_of_group_tax(self):
        self.fixed_tax.include_base_amount = True
        res = self.group_of_group_tax.compute_all(200.0)
        self._check_compute_all_results(
            263,    # 'total_included'
            200,    # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (200.0, 10.0),    # |  1  |    10  |      |     t
                (210.0, 21.0),    # |  3  |    10% |      |
                (210.0, 10.0),    # |  1  |    10  |      |     t
                (220.0, 22.0),    # |  3  |    10% |      |
                # ---------------------------------------------------
            ],
            res
        )

    def test_tax_group(self):
        res = self.group_tax.compute_all(200.0)
        self._check_compute_all_results(
            230,    # 'total_included'
            200,    # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (200.0, 10.0),    # |  1  |    10  |      |
                (200.0, 20.0),    # |  3  |    10% |      |
                # ---------------------------------------------------
            ],
            res
        )

    def test_tax_group_percent(self):
        res = self.group_tax_percent.with_context({'force_price_include':True}).compute_all(100.0)
        self._check_compute_all_results(
            100,    # 'total_included'
            83.33,    # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (83.33, 8.33),    # |  1  |    10% |      |
                (83.33, 8.34),    # |  2  |    10% |      |
                # ---------------------------------------------------
            ],
            res
        )

    def test_tax_percent_division(self):
        self.division_tax.price_include = True
        self.division_tax.include_base_amount = True
        res_division = self.division_tax.compute_all(200.0)
        self._check_compute_all_results(
            200,    # 'total_included'
            180,    # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (180.0, 20.0),    # |  4  |    10/ |   t  |     t
                # ---------------------------------------------------
            ],
            res_division
        )
        self.percent_tax.price_include = False
        self.percent_tax.include_base_amount = False
        res_percent = self.percent_tax.compute_all(100.0)
        self._check_compute_all_results(
            110,    # 'total_included'
            100,    # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (100.0, 10.0),    # |  3  |    10% |      |
                # ---------------------------------------------------
            ],
            res_percent
        )
        self.division_tax.price_include = False
        self.division_tax.include_base_amount = False
        res_division = self.division_tax.compute_all(180.0)
        self._check_compute_all_results(
            200,    # 'total_included'
            180,    # 'total_excluded'
            [
                # base, amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (180.0, 20.0),   # |  4  |    10/ |      |
                # ---------------------------------------------------
            ],
            res_division
        )
        self.percent_tax.price_include = True
        self.percent_tax.include_base_amount = True
        res_percent = self.percent_tax.compute_all(110.0)
        self._check_compute_all_results(
            110,    # 'total_included'
            100,    # 'total_excluded'
            [
                # base, amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (100.0, 10.0),   # |  3  |    10% |   t  |     t
                # ---------------------------------------------------
            ],
            res_percent
        )
        self.percent_tax_bis.price_include = True
        self.percent_tax_bis.include_base_amount = True
        self.percent_tax_bis.amount = 21
        res_percent = self.percent_tax_bis.compute_all(7.0)
        self._check_compute_all_results(
            7.0,   # 'total_included'
            5.79,  # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (5.79, 1.21),     # |  3  |    21% |   t  |     t
                # ---------------------------------------------------
            ],
            res_percent
        )

    def test_tax_sequence_normalized_set(self):
        self.division_tax.sequence = 1
        self.fixed_tax.sequence = 2
        self.percent_tax.sequence = 3
        taxes_set = (self.group_tax | self.division_tax)
        res = taxes_set.compute_all(200.0)
        self._check_compute_all_results(
            252.22,  # 'total_included'
            200,     # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (200.0, 22.22),   # |  1  |    10/ |      |
                (200.0, 10.0),    # |  2  |    10  |      |
                (200.0, 20.0),    # |  3  |    10% |      |
                # ---------------------------------------------------
            ],
            res
        )

    def test_fixed_tax_include_base_amount(self):
        self.fixed_tax.include_base_amount = True
        res = self.group_tax.compute_all(200.0)
        self._check_compute_all_results(
            231,     # 'total_included'
            200,     # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (200.0, 10.0),    # |  1  |    10  |      |     t
                (210.0, 21.0),    # |  3  |    10% |      |
                # ---------------------------------------------------
            ],
            res
        )

        self.fixed_tax.price_include = True
        self.fixed_tax.include_base_amount = False
        res = self.fixed_tax.compute_all(100.0, quantity=2.0)
        self._check_compute_all_results(
            200,     # 'total_included'
            180,     # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (180.0, 20.0),    # |  1  |    20  |      |     t
                # ---------------------------------------------------
            ],
            res
        )

    def test_percent_tax_include_base_amount(self):
        self.percent_tax.price_include = True
        self.percent_tax.amount = 21.0
        res = self.percent_tax.compute_all(7.0)
        self._check_compute_all_results(
            7.0,      # 'total_included'
            5.79,     # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (5.79, 1.21),     # |  3  |    21% |   t  |
                # ---------------------------------------------------
            ],
            res
        )

        self.percent_tax.price_include = True
        self.percent_tax.amount = 20.0
        res = self.percent_tax.compute_all(399.99)
        self._check_compute_all_results(
            399.99,     # 'total_included'
            333.33,     # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (333.33, 66.66),  # |  3  |    20% |   t  |
                # ---------------------------------------------------
            ],
            res
        )

    def test_tax_decimals(self):
        """Test the rounding of taxes up to 6 decimals (maximum decimals places allowed for currencies)"""
        self.env.user.company_id.currency_id.rounding = 0.000001

        self.percent_tax.price_include = True
        self.percent_tax.amount = 21.0
        res = self.percent_tax.compute_all(7.0)
        self._check_compute_all_results(
            7.0,          # 'total_included'
            5.785124,     # 'total_excluded'
            [
                # base , amount          | seq | amount | incl | incl_base
                # --------------------------------------------------------
                (5.785124, 1.214876),  # |  3  |    21% |   t  |
                # --------------------------------------------------------
            ],
            res
        )

        self.percent_tax.price_include = True
        self.percent_tax.amount = 20.0
        res = self.percent_tax.compute_all(399.999999)
        self._check_compute_all_results(
            399.999999,     # 'total_included'
            333.333333,     # 'total_excluded'
            [
                # base , amount             | seq | amount | incl | incl_base
                # -----------------------------------------------------------
                (333.333333, 66.666666),  # |  3  |    20% |   t  |
                # -----------------------------------------------------------
            ],
            res
        )

    def test_advanced_taxes_computation_0(self):
        '''Test more advanced taxes computation (see issue 34471).'''
        tax_1 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_1',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
            'sequence': 1,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
        })
        tax_2 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_2',
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 2,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
        })
        tax_3 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_3',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'sequence': 3,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
        })
        tax_4 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_4',
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 4,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
        })
        tax_5 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_5',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'sequence': 5,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
        })
        taxes = tax_1 + tax_2 + tax_3 + tax_4 + tax_5

        # Test with positive amount.
        self._check_compute_all_results(
            154,     # 'total_included'
            100,     # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (100.0, 5.0),     # |  1  |    10% |   t  |     t
                (100.0, 5.0),     # |  1  |    10% |   t  |     t
                (110.0, 5.5),     # |  2  |    10% |      |
                (110.0, 5.5),     # |  2  |    10% |      |
                (110.0, 5.5),     # |  3  |    10% |   t  |
                (110.0, 5.5),     # |  3  |    10% |   t  |
                (110.0, 5.5),     # |  4  |    10% |      |
                (110.0, 5.5),     # |  4  |    10% |      |
                (110.0, 5.5),     # |  5  |    10% |   t  |
                (110.0, 5.5),     # |  5  |    10% |   t  |
                # ---------------------------------------------------
            ],
            taxes.compute_all(132.0)
        )

        # Test with negative amount.
        self._check_compute_all_results(
            -154,    # 'total_included'
            -100,    # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (-100.0, -5.0),   # |  1  |    10% |   t  |     t
                (-100.0, -5.0),   # |  1  |    10% |   t  |     t
                (-110.0, -5.5),   # |  2  |    10% |      |
                (-110.0, -5.5),   # |  2  |    10% |      |
                (-110.0, -5.5),   # |  3  |    10% |   t  |
                (-110.0, -5.5),   # |  3  |    10% |   t  |
                (-110.0, -5.5),   # |  4  |    10% |      |
                (-110.0, -5.5),   # |  4  |    10% |      |
                (-110.0, -5.5),   # |  5  |    10% |   t  |
                (-110.0, -5.5),   # |  5  |    10% |   t  |
                # ---------------------------------------------------
            ],
            taxes.compute_all(-132.0)
        )

    def test_intracomm_taxes_computation_0(self):
        ''' Test usage of intracomm taxes having e.g.+100%, -100% as repartition lines. '''
        intracomm_tax = self.env['account.tax'].create({
            'name': 'test_intracomm_taxes_computation_0_1',
            'amount_type': 'percent',
            'amount': 21,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        })

        # Test with positive amount.
        self._check_compute_all_results(
            100,     # 'total_included'
            100,     # 'total_excluded'
            [
                # base , amount
                # ---------------
                (100.0, 21.0),
                (100.0, -21.0),
                # ---------------
            ],
            intracomm_tax.compute_all(100.0)
        )

        # Test with negative amount.
        self._check_compute_all_results(
            -100,    # 'total_included'
            -100,    # 'total_excluded'
            [
                # base , amount
                # ---------------
                (-100.0, -21.0),
                (-100.0, 21.0),
                # ---------------
            ],
            intracomm_tax.compute_all(-100.0)
        )

    def test_rounding_issues_0(self):
        ''' Test taxes having a complex setup of repartition lines. '''
        tax = self.env['account.tax'].create({
            'name': 'test_rounding_issues_0',
            'amount_type': 'percent',
            'amount': 3,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
        })

        # Test with positive amount.
        self._check_compute_all_results(
            1.09,   # 'total_included'
            1,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (1.0, 0.01),
                (1.0, 0.01),
                (1.0, 0.01),
                (1.0, 0.02),
                (1.0, 0.02),
                (1.0, 0.02),
                # ---------------
            ],
            tax.compute_all(1.0)
        )

        # Test with negative amount.
        self._check_compute_all_results(
            -1.09,  # 'total_included'
            -1,     # 'total_excluded'
            [
                # base , amount
                # ---------------
                (-1.0, -0.01),
                (-1.0, -0.01),
                (-1.0, -0.01),
                (-1.0, -0.02),
                (-1.0, -0.02),
                (-1.0, -0.02),
                # ---------------
            ],
            tax.compute_all(-1.0)
        )

    def test_rounding_issues_1(self):
        ''' Test taxes having a complex setup of repartition lines. '''
        tax = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_repartition_lines_computation_1',
            'amount_type': 'percent',
            'amount': 3,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 25.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 25.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -25.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -25.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -50.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 25.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 25.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -25.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -25.0}),
            ],
        })

        # Test with positive amount.
        self._check_compute_all_results(
            1,      # 'total_included'
            1,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (1.0, 0.02),
                (1.0, -0.02),
                (1.0, 0.01),
                (1.0, 0.01),
                (1.0, -0.01),
                (1.0, -0.01),
                # ---------------
            ],
            tax.compute_all(1.0)
        )

        # Test with negative amount.
        self._check_compute_all_results(
            -1,     # 'total_included'
            -1,     # 'total_excluded'
            [
                # base , amount
                # ---------------
                (-1.0, -0.02),
                (-1.0, 0.02),
                (-1.0, -0.01),
                (-1.0, -0.01),
                (-1.0, 0.01),
                (-1.0, 0.01),
                # ---------------
            ],
            tax.compute_all(-1.0)
        )

    def test_rounding_tax_excluded_round_per_line_01(self):
        ''' Test the rounding of a 19% price excluded tax in an invoice having 22689 and 9176 as lines.
        The decimal precision is set to zero.
        The computation must be similar to round(22689 * 0.19) + round(9176 * 0.19).
        '''
        self.tax_19_percent.company_id.currency_id.rounding = 1.0
        self.tax_19_percent.company_id.tax_calculation_rounding_method = 'round_per_line'

        res1 = self.tax_19_percent.compute_all(22689)
        self._check_compute_all_results(
            27000,      # 'total_included'
            22689,      # 'total_excluded'
            [
                # base, amount
                # ---------------
                (22689, 4311),
                # ---------------
            ],
            res1
        )

        res2 = self.tax_19_percent.compute_all(9176)
        self._check_compute_all_results(
            10919,      # 'total_included'
            9176,       # 'total_excluded'
            [
                # base , amount
                # ---------------
                (9176,  1743),
                # ---------------
            ],
            res2
        )

    def test_rounding_tax_excluded_round_globally(self):
        ''' Test the rounding of a 19% price excluded tax in an invoice having 22689 and 9176 as lines.
        The decimal precision is set to zero.
        The computation must be similar to round((22689 + 9176) * 0.19).
        '''
        self.tax_19_percent.company_id.tax_calculation_rounding_method = 'round_globally'

        res1 = self.tax_19_percent.compute_all(22689)
        self._check_compute_all_results(
            27000,      # 'total_included'
            22689,      # 'total_excluded'
            [
                # base, amount
                # ---------------
                (22689, 4310.91),
                # ---------------
            ],
            res1
        )

        res2 = self.tax_19_percent.compute_all(9176)
        self._check_compute_all_results(
            10919,      # 'total_included'
            9176,       # 'total_excluded'
            [
                # base , amount
                # ---------------
                (9176,  1743.44),
                # ---------------
            ],
            res2
        )

    def test_rounding_tax_included_round_per_line_01(self):
        ''' Test the rounding of a 19% price included tax in an invoice having 27000 and 10920 as lines.
        The decimal precision is set to zero.
        The computation must be similar to round(27000 / 1.19) + round(10920 / 1.19).
        '''
        self.tax_19_percent.price_include = True
        self.tax_19_percent.company_id.currency_id.rounding = 1.0
        self.tax_19_percent.company_id.tax_calculation_rounding_method = 'round_per_line'

        res1 = self.tax_19_percent.compute_all(27000)
        self._check_compute_all_results(
            27000,      # 'total_included'
            22689,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (22689, 4311),
                # ---------------
            ],
            res1
        )

        res2 = self.tax_19_percent.compute_all(10920)
        self._check_compute_all_results(
            10920,      # 'total_included'
            9176,       # 'total_excluded'
            [
                # base , amount
                # ---------------
                (9176,  1744),
                # ---------------
            ],
            res2
        )

    def test_rounding_tax_included_round_per_line_02(self):
        ''' Test the rounding of a 12% price included tax in an invoice having 52.50 as line.
        The decimal precision is set to 2.
        '''
        self.tax_12_percent.price_include = True
        self.tax_12_percent.company_id.currency_id.rounding = 0.01

        res1 = self.tax_12_percent.compute_all(52.50)
        self._check_compute_all_results(
            52.50,      # 'total_included'
            46.88,      # 'total_excluded'
            [
                # base , amount
                # -------------
                (46.88, 5.62),
                # -------------
            ],
            res1
        )

    def test_rounding_tax_included_round_per_line_03(self):
        ''' Test the rounding of a 8% and 0% price included tax in an invoice having 8 * 15.55 as line.
        The decimal precision is set to 2.
        '''
        self.tax_0_percent.company_id.currency_id.rounding = 0.01
        self.tax_0_percent.price_include = True
        self.tax_8_percent.price_include = True

        self.group_tax.children_tax_ids = [(6, 0, self.tax_0_percent.ids)]
        self.group_tax_bis.children_tax_ids = [(6, 0, self.tax_8_percent.ids)]

        res1 = (self.tax_8_percent | self.tax_0_percent).compute_all(15.55, quantity=8.0)
        self._check_compute_all_results(
            124.40,      # 'total_included'
            115.19,      # 'total_excluded'
            [
                # base , amount
                # -------------
                (115.19, 9.21),
                (115.19, 0.00),
                # -------------
            ],
            res1
        )

        res2 = (self.tax_0_percent | self.tax_8_percent).compute_all(15.55, quantity=8.0)
        self._check_compute_all_results(
            124.40,      # 'total_included'
            115.19,      # 'total_excluded'
            [
                # base , amount
                # -------------
                (115.19, 0.00),
                (115.19, 9.21),
                # -------------
            ],
            res2
        )

    def test_rounding_tax_included_round_per_line_04(self):
        ''' Test the rounding of a 5% price included tax.
        The decimal precision is set to 0.05.
        '''
        self.tax_5_percent.price_include = True
        self.tax_5_percent.company_id.currency_id.rounding = 0.05
        self.tax_5_percent.company_id.tax_calculation_rounding_method = 'round_per_line'

        res1 = self.tax_5_percent.compute_all(5)
        self._check_compute_all_results(
            5,      # 'total_included'
            4.75,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (4.75, 0.25),
                # ---------------
            ],
            res1
        )

        res2 = self.tax_5_percent.compute_all(10)
        self._check_compute_all_results(
            10,      # 'total_included'
            9.5,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (9.5, 0.5),
                # ---------------
            ],
            res2
        )

        res3 = self.tax_5_percent.compute_all(50)
        self._check_compute_all_results(
            50,      # 'total_included'
            47.6,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (47.6, 2.4),
                # ---------------
            ],
            res3
        )

    def test_rounding_tax_included_round_globally_01(self):
        ''' Test the rounding of a 19% price included tax in an invoice having 27000 and 10920 as lines.
        The decimal precision is set to zero.
        The computation must be similar to round((27000 + 10920) / 1.19).
        '''
        self.tax_19_percent.price_include = True
        self.tax_19_percent.company_id.tax_calculation_rounding_method = 'round_globally'

        res1 = self.tax_19_percent.compute_all(27000)
        self._check_compute_all_results(
            27000,      # 'total_included'
            22689,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (22689, 4311),
                # ---------------
            ],
            res1
        )

        res2 = self.tax_19_percent.compute_all(10920)
        self._check_compute_all_results(
            10920,      # 'total_included'
            9176,       # 'total_excluded'
            [
                # base , amount
                # ---------------
                (9176,  1744),
                # ---------------
            ],
            res2
        )

    def test_rounding_tax_included_round_globally_02(self):
        ''' Test the rounding of a 21% price included tax in an invoice having 11.90 and 2.80 as lines.
        The decimal precision is set to 2.
        '''
        self.tax_21_percent.price_include = True
        self.tax_21_percent.company_id.currency_id.rounding = 0.01
        self.tax_21_percent.company_id.tax_calculation_rounding_method = 'round_globally'

        res1 = self.tax_21_percent.compute_all(11.90)
        self._check_compute_all_results(
            11.90,      # 'total_included'
            9.83,       # 'total_excluded'
            [
                # base , amount
                # ---------------
                (9.83, 2.07),
                # ---------------
            ],
            res1
        )

        res2 = self.tax_21_percent.compute_all(2.80)
        self._check_compute_all_results(
            2.80,      # 'total_included'
            2.31,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (2.31,  0.49),
                # ---------------
            ],
            res2
        )

    def test_rounding_tax_included_round_globally_03(self):
        ''' Test the rounding of a 5% price included tax.
        The decimal precision is set to 0.05.
        '''
        self.tax_5_percent.price_include = True
        self.tax_5_percent.company_id.currency_id.rounding = 0.05
        self.tax_5_percent.company_id.tax_calculation_rounding_method = 'round_globally'

        res1 = self.tax_5_percent.compute_all(5)
        self._check_compute_all_results(
            5,      # 'total_included'
            4.75,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (4.75, 0.25),
                # ---------------
            ],
            res1
        )

        res2 = self.tax_5_percent.compute_all(10)
        self._check_compute_all_results(
            10,      # 'total_included'
            9.5,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (9.50, 0.50),
                # ---------------
            ],
            res2
        )

        res3 = self.tax_5_percent.compute_all(50)
        self._check_compute_all_results(
            50,      # 'total_included'
            47.6,      # 'total_excluded'
            [
                # base , amount
                # ---------------
                (47.60, 2.40),
                # ---------------
            ],
            res3
        )

    def test_is_base_affected(self):
        taxes = self.env['account.tax'].create([{
            'name': 'test_is_base_affected%s' % i,
            'amount_type': 'percent',
            'amount': amount,
            'include_base_amount': include_base_amount,
            'is_base_affected': is_base_affected,
            'sequence': i,
        } for i, amount, include_base_amount, is_base_affected in [
            (0, 6, True, True),
            (1, 6, True, False),
            (2, 10, False, True),
        ]])

        compute_all_results = taxes.compute_all(100.0)

        # Check the balance of the generated move lines
        self._check_compute_all_results(
            123.2,      # 'total_included'
            100.0,      # 'total_excluded'
            [
                # base, amount
                # -------------------------
                (100.0, 6.0),
                (100.0, 6.0),
                (112.0, 11.2),
                # -------------------------
            ],
            compute_all_results,
        )

        # Check the tax_ids on tax lines
        expected_tax_ids_list = [taxes[2].ids, taxes[2].ids, []]
        tax_ids_list = [tax_line['tax_ids'] for tax_line in compute_all_results['taxes']]
        self.assertEqual(tax_ids_list, expected_tax_ids_list, "Only a tax affected by previous taxes should have tax_ids set on its tax line when used after an 'include_base_amount' tax.")

    def test_mixing_price_included_excluded_with_affect_base(self):
        tax_10_fix = self.env['account.tax'].create({
            'name': "tax_10_fix",
            'amount_type': 'fixed',
            'amount': 10.0,
            'include_base_amount': True,
        })
        tax_21 = self.env['account.tax'].create({
            'name': "tax_21",
            'amount_type': 'percent',
            'amount': 21.0,
            'price_include': True,
            'include_base_amount': True,
        })

        self._check_compute_all_results(
            1222.1,     # 'total_included'
            1000.0,     # 'total_excluded'
            [
                # base , amount
                # ---------------
                (1000.0, 10.0),
                (1010.0, 212.1),
                # ---------------
            ],
            (tax_10_fix + tax_21).compute_all(1210),
        )

    def test_price_included_repartition_sum_0(self):
        """ Tests the case where a tax with a non-zero value has a sum
        of tax repartition factors of zero and is included in price. It
        shouldn't behave in the same way as a 0% tax.
        """
        test_tax = self.env['account.tax'].create({
            'name': "Definitely not a 0% tax",
            'amount_type': 'percent',
            'amount': 42,
            'price_include': True,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),

                (0, 0, {'repartition_type': 'tax'}),

                (0, 0, {
                    'factor_percent': -100,
                    'repartition_type': 'tax',
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),

                (0, 0, {'repartition_type': 'tax'}),

                (0, 0, {
                    'factor_percent': -100,
                    'repartition_type': 'tax',
                }),
            ],
        })

        compute_all_res = test_tax.compute_all(100)
        self._check_compute_all_results(
            100,         # 'total_included'
            100,         # 'total_excluded'
            [
                # base , amount
                # ---------------
                (100, 42),
                (100, -42),
                # ---------------
            ],
            compute_all_res
        )

    def test_parse_name_search(self):
        list_ten_fixed_tax = self.env["account.tax"]
        ten_fixed_tax = self.env["account.tax"].create(
            {"name": "Ten Fixed tax", "amount_type": "fixed", "amount": 10}
        )
        list_ten_fixed_tax |= ten_fixed_tax
        ten_fixed_tax_tix = self.env["account.tax"].create(
            {"name": "Ten Fixed tax tix", "amount_type": "fixed", "amount": 10}
        )
        list_ten_fixed_tax |= ten_fixed_tax_tix

        self.assertListEqual(
            [x[0] for x in self.env["account.tax"].name_search("tix")],
            list_ten_fixed_tax.ids,
        )
        self.assertListEqual(
            [x[0] for x in self.env["account.tax"].name_search("\"tix\"")],
            ten_fixed_tax_tix.ids,
        )
        self.assertListEqual(
            [x[0] for x in self.env["account.tax"].name_search("Ten \"tix\"")],
            ten_fixed_tax_tix.ids,
        )
