# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSetupBar(AccountingTestCase):

    def test_initial_balance_step(self):
        company = self.env.ref('base.main_company')
        company.create_op_move_if_non_existant()
        initial_setup_wizard = self.env['account.opening'].create({'company_id': company.id}).with_context({'check_move_validity': False})

        unaffected_earnings_type = self.env.ref("account.data_unaffected_earnings")
        account = self.env['account.account'].search([('user_type_id', '!=', unaffected_earnings_type.id)], limit=1)

        # Adding the first line creates a new automatic adjustment line balancing the move
        test_line_1 = self.env['account.move.line'].with_context({'check_move_validity': False}).create({
                        'name': 'Test line 1',
                        'move_id': company.account_opening_move_id.id,
                        'account_id': account.id,
                        'debit': 42.0,
                        'credit': 0.0,
                        'company_id': company.id,
                    })
        initial_setup_wizard.opening_move_line_ids_changed()

        self.assertEqual(len(initial_setup_wizard.opening_move_line_ids), 2, "The wizard should contain 2 lines: 1 manually created, and 1 automatic adjustment.")
        automatic_line = initial_setup_wizard.opening_move_line_ids.filtered(lambda x: x != test_line_1)
        self.assertEqual(automatic_line.account_id.user_type_id, unaffected_earnings_type, "Automatic adjustment line should be of type 'current year earnings'.")
        self.assertEqual(automatic_line.credit, 42.0, "Automatic line should balance opening move.")
        self.assertEqual(automatic_line.debit, 0.0, "Automatic line should balance opening move.")

        # Adding a new line modifies the amount of the already existing adjustment line
        test_line_2 = self.env['account.move.line'].with_context({'check_move_validity': False}).create({
                        'name': 'Test line 2',
                        'move_id': company.account_opening_move_id.id,
                        'account_id': account.id,
                        'debit': 0.0,
                        'credit': 12.0,
                        'company_id': company.id,
                    })
        initial_setup_wizard.opening_move_line_ids_changed()

        self.assertEqual(len(initial_setup_wizard.opening_move_line_ids), 3, "The wizard should contain 3 lines: 2 manually created, and 1 automatic adjustment.")
        self.assertTrue(automatic_line in initial_setup_wizard.opening_move_line_ids, "Automatic line should stay the same when adding a new line.")
        self.assertEqual(automatic_line.credit, 30.0, "Automatic line should balance opening move.")
        self.assertEqual(automatic_line.debit, 0.0, "Automatic line should balance opening move.")

        # When a new line balances the move, the adjustment line gets automatically removed
        test_line_3 = self.env['account.move.line'].with_context({'check_move_validity': False}).create({
                        'name': 'Test line 3',
                        'move_id': company.account_opening_move_id.id,
                        'account_id': account.id,
                        'debit': 0.0,
                        'credit': 30.0,
                        'company_id': company.id,
                    })
        initial_setup_wizard.opening_move_line_ids_changed()

        self.assertEqual(len(initial_setup_wizard.opening_move_line_ids), 3, "The wizard should contain 3 lines: 3 manually created, and 0 automatic adjustment.")
        self.assertFalse(automatic_line in initial_setup_wizard.opening_move_line_ids, "Automatic adjustment line should be removed when useless.")

        # The opening move stays balanced at any time
        test_line_4 = self.env['account.move.line'].with_context({'check_move_validity': False}).create({
                        'name': 'Test line 4',
                        'move_id': company.account_opening_move_id.id,
                        'account_id': account.id,
                        'debit': 11.0,
                        'credit': 0.0,
                        'company_id': company.id,
                    })
        initial_setup_wizard.opening_move_line_ids_changed()
        initial_setup_wizard.validate()
        company.account_opening_move_id.assert_balanced()
