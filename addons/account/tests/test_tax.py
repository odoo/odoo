# -*- coding: utf-8 -*-

from odoo.addons.account.tests.account_test_users import AccountTestUsers

import time


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
            'amount': 21,
            'sequence': 3,
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
        self.bank_journal = self.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', self.account_manager.company_id.id)])[0]
        self.bank_account = self.bank_journal.default_debit_account_id
        self.expense_account = self.env['account.account'].search([('user_type_id.type', '=', 'payable')], limit=1) #Should be done by onchange later

    def _check_compute_all_results(self, base, total_included, total_excluded, taxes, res):
        self.assertAlmostEqual(res['base'], base)
        self.assertAlmostEqual(res['total_included'], total_included)
        self.assertAlmostEqual(res['total_excluded'], total_excluded)
        for i in range(0, len(taxes)):
            self.assertAlmostEqual(res['taxes'][i]['base'], taxes[i][0])
            self.assertAlmostEqual(res['taxes'][i]['amount'], taxes[i][1])

    def test_tax_group_of_group_tax(self):
        self.fixed_tax.include_base_amount = True
        res = self.group_of_group_tax.compute_all(200.0)
        self._check_compute_all_results(
            220,    # 'base'
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
            200,    # 'base'
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
            220,    # 'base'
            220,    # 'total_included'
            200,    # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (200.0, 20.0),    # |  4  |    10/ |   t  |     t
                # ---------------------------------------------------
            ],
            res_division
        )
        self.percent_tax.price_include = False
        self.percent_tax.include_base_amount = False
        res_percent = self.percent_tax.compute_all(200.0)
        self._check_compute_all_results(
            200,    # 'base'
            220,    # 'total_included'
            200,    # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (200.0, 20.0),    # |  3  |    10% |      |
                # ---------------------------------------------------
            ],
            res_percent
        )
        self.division_tax.price_include = False
        self.division_tax.include_base_amount = False
        res_division = self.division_tax.compute_all(200.0)
        self._check_compute_all_results(
            200,     # 'base'
            222.22,  # 'total_included'
            200,     # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (200.0, 22.22),   # |  4  |    10/ |      |
                # ---------------------------------------------------
            ],
            res_division
        )
        self.percent_tax.price_include = True
        self.percent_tax.include_base_amount = True
        res_percent = self.percent_tax.compute_all(200.0)
        self._check_compute_all_results(
            200,     # 'base'
            200,     # 'total_included'
            181.82,  # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (181.82, 18.18),  # |  3  |    10% |   t  |     t
                # ---------------------------------------------------
            ],
            res_percent
        )
        self.percent_tax_bis.price_include = True
        self.percent_tax_bis.include_base_amount = True
        res_percent = self.percent_tax_bis.compute_all(7.0)
        self._check_compute_all_results(
            7.0,   # 'base'
            7.0,   # 'total_included'
            5.79,  # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (5.79, 1.21),  # |  3  |    21% |   t  |     t
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
            200,     # 'base'
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

    def test_tax_include_base_amount(self):
        self.fixed_tax.include_base_amount = True
        res = self.group_tax.compute_all(200.0)
        self._check_compute_all_results(
            210,     # 'base'
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

    def test_tax_currency(self):
        self.division_tax.amount = 15.0
        res = self.division_tax.compute_all(200.0, currency=self.env.ref('base.VEF'))
        self._check_compute_all_results(
            200,       # 'base'
            235.2941,  # 'total_included'
            200,       # 'total_excluded'
            [
                # base , amount      | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (200.0, 35.2941),  # |  4  |    15/ |      |
                # ---------------------------------------------------
            ],
            res
        )

    def test_tax_move_lines_creation(self):
        """ Test that creating a move.line with tax_ids generates the tax move lines and adjust line amount when a tax is price_include """

        self.fixed_tax.price_include = True
        self.fixed_tax.include_base_amount = True
        company_id = self.env['res.users'].browse(self.env.uid).company_id.id
        vals = {
            'date': time.strftime('%Y-01-01'),
            'journal_id': self.bank_journal.id,
            'name': 'Test move',
            'line_ids': [(0, 0, {
                    'account_id': self.bank_account.id,
                    'debit': 235,
                    'credit': 0,
                    'name': 'Bank Fees',
                    'partner_id': False,
                }), (0, 0, {
                    'account_id': self.expense_account.id,
                    'debit': 0,
                    'credit': 200,
                    'date': time.strftime('%Y-01-01'),
                    'name': 'Bank Fees',
                    'partner_id': False,
                    'tax_ids': [(4, self.group_tax.id), (4, self.fixed_tax_bis.id)]
                })],
            'company_id': company_id,
        }
        move = self.env['account.move'].with_context(apply_taxes=True).create(vals)


        aml_fixed_tax = move.line_ids.filtered(lambda l: l.tax_line_id.id == self.fixed_tax.id)
        aml_percent_tax = move.line_ids.filtered(lambda l: l.tax_line_id.id == self.percent_tax.id)
        aml_fixed_tax_bis = move.line_ids.filtered(lambda l: l.tax_line_id.id == self.fixed_tax_bis.id)
        self.assertEquals(len(aml_fixed_tax), 1)
        self.assertEquals(aml_fixed_tax.credit, 10)
        self.assertEquals(len(aml_percent_tax), 1)
        self.assertEquals(aml_percent_tax.credit, 20)
        self.assertEquals(len(aml_fixed_tax_bis), 1)
        self.assertEquals(aml_fixed_tax_bis.credit, 15)
        
        aml_with_taxes = move.line_ids.filtered(lambda l: set(l.tax_ids.ids) == set([self.group_tax.id, self.fixed_tax_bis.id]))
        self.assertEquals(len(aml_with_taxes), 1)
        self.assertEquals(aml_with_taxes.credit, 190)

    def test_advanced_taxes_computation_0(self):
        '''Test more advanced taxes computation (see issue 34471).'''
        tax_1 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_1',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
            'sequence': 1,
        })
        tax_2 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_2',
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 2,
        })
        tax_3 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_3',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'sequence': 3,
        })
        tax_4 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_4',
            'amount_type': 'percent',
            'amount': 10,
            'sequence': 4,
        })
        tax_5 = self.env['account.tax'].create({
            'name': 'test_advanced_taxes_computation_0_5',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'sequence': 5,
        })
        taxes = tax_1 + tax_2 + tax_3 + tax_4 + tax_5
        res = taxes.compute_all(132.0)
        self._check_compute_all_results(
            110,     # 'base'
            154,     # 'total_included'
            100,     # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (100.0, 10.0),    # |  1  |    10% |   t  |     t
                (110.0, 11.0),    # |  3  |    10% |      |
                (110.0, 11.0),    # |  3  |    10% |   t  |
                (110.0, 11.0),    # |  3  |    10% |      |
                (110.0, 11.0),    # |  3  |    10% |   t  |
                # ---------------------------------------------------
            ],
            res
        )
