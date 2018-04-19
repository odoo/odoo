# -*- coding: utf-8 -*-

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveUnalterable(AccountingTestCase):
    def setUp(self):
        super(TestAccountMoveUnalterable, self).setUp()
        self.env.user.company_id.country_id = self.env.ref('base.fr')

    def _create_move_line_vals(self, debit, credit):
        company = self.env.user.company_id
        account = self.env['account.account'].search([('company_id', '=', company.id)], limit=1)
        return {
            'name': fields.Date.today(),
            'debit': debit,
            'credit': credit,
            'account_id': account.id,
        }

    def _create_move(self):
        company = self.env.user.company_id
        journal = self.env['account.journal'].search([('company_id', '=', company.id)], limit=1)
        return self.env['account.move'].create({
            'journal_id': journal.id,
            'line_ids': [(0, 0, self._create_move_line_vals(42, 0)), (0, 0, self._create_move_line_vals(0, 42))],
        })

    def test_unalterable_move(self):
        move = self._create_move()

        self.assertFalse(move.unalterable_sequence_number)
        self.assertFalse(move.unalterable_hash)

        move.post()

        self.assertTrue(move.unalterable_sequence_number)
        self.assertTrue(move.unalterable_hash)

        with self.assertRaises(UserError):
            move.unlink()

        with self.assertRaises(UserError):
            move.button_cancel()

        with self.assertRaises(UserError):
            field = move._get_unalterable_fields()
            vals = {field[0]: 'test'}
            move.write(vals)
