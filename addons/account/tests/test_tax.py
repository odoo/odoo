# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_users import AccountTestUsers
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTax(AccountTestUsers):

    def setUp(self):
        super(TestTax, self).setUp()

        self.fixed_tax = self.tax_model.create({
            'name': "Fixed tax",
            'amount_type': 'fixed',
            'amount': 10,
            'sequence': 1,
        })
        self.fixed_tax_bis = self.tax_model.create({
            'name': "Fixed tax bis",
            'amount_type': 'fixed',
            'amount': 15,
            'sequence': 2,
        })
        self.percent_tax = self.tax_model.create({
            'name': "Percent tax",
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 3,
        })
        self.percent_tax_bis = self.tax_model.create({
            'name': "Percent tax bis",
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 4,
        })
        self.division_tax = self.tax_model.create({
            'name': "Division tax",
            'amount_type': 'division',
            'amount': 10,
            'sequence': 4,
        })
        self.group_tax = self.tax_model.create({
            'name': "Group tax",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 5,
            'children_tax_ids': [
                (4, self.fixed_tax.id, 0),
                (4, self.percent_tax.id, 0)
            ]
        })
        self.group_tax_bis = self.tax_model.create({
            'name': "Group tax bis",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 6,
            'children_tax_ids': [
                (4, self.fixed_tax.id, 0),
                (4, self.percent_tax.id, 0)
            ]
        })
        self.group_of_group_tax = self.tax_model.create({
            'name': "Group of group tax",
            'amount_type': 'group',
            'amount': 0,
            'sequence': 7,
            'children_tax_ids': [
                (4, self.group_tax.id, 0),
                (4, self.group_tax_bis.id, 0)
            ]
        })
        self.tax_with_no_account = self.tax_model.create({
            'name': "Tax with no account",
            'amount_type': 'fixed',
            'amount': 0,
            'sequence': 8,
        })
        some_account = self.env['account.account'].search([], limit=1)
        self.tax_with_account = self.tax_model.create({
            'name': "Tax with account",
            'amount_type': 'fixed',
            'amount': 0,
            'sequence': 8,
            'invoice_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': some_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'account_id': some_account.id,
                }),
            ],
        })
        self.bank_journal = self.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', self.account_manager.company_id.id)])[0]
        self.bank_account = self.bank_journal.default_debit_account_id
        self.expense_account = self.env['account.account'].search([('user_type_id.type', '=', 'payable')], limit=1) #Should be done by onchange later

    def _check_compute_all_results(self, total_included, total_excluded, taxes, res):
        self.assertAlmostEqual(res['total_included'], total_included)
        self.assertAlmostEqual(res['total_excluded'], total_excluded)
        for i in range(0, len(taxes)):
            self.assertAlmostEqual(res['taxes'][i]['base'], taxes[i][0])
            self.assertAlmostEqual(res['taxes'][i]['amount'], taxes[i][1])

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
