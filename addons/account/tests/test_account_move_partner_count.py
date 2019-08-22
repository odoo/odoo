# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestAccountMovePartnerCount(TransactionCase):

    def setUp(self):
        super().setUp()

        # T1 Create partner and account move
        # (Use a new cursor to make sure creations are committed for later transactions)
        with self.registry.cursor() as cr:
            env = self.env(cr=cr)
            self.partner = self.env['res.partner'].with_env(env).create({'name': 'Lucien'})
            user_type_income = env.ref('account.data_account_type_direct_costs')
            self.account_income = self.env['account.account'].with_env(env).create({
                'code': 'TESTCOUNT42',
                'name': 'Sale - Test Account',
                'user_type_id': user_type_income.id
            })

            self.journal = self.env['account.journal'].with_env(env).create({
                'name': 'Journal',
                'code': '7775',
                'type': 'sale',
            })
            self.move = self.env['account.move'].with_env(env).create({
                'partner_id': self.partner.id,
                'type': 'out_invoice',
                'journal_id': self.journal.id,
                'currency_id': self.env.user.company_id.currency_id.id,
            })
            self.line = self.env['account.move.line'].with_env(env).create({
                'move_id': self.move.id,
                'name': 'account move line test',
                'account_id': self.account_income.id,
            })

    def tearDown(self):
        super().tearDown()
        with self.registry.cursor() as cr:
            env = self.env(cr=cr)
            move = self.move.with_env(env)
            move.name = '/'
            move.state = 'draft'
            move.unlink()
            self.journal.with_env(env).unlink()
            self.account_income.with_env(env).unlink()
            self.partner.with_env(env).unlink()

    def test_account_move_count(self):
        # T2 create and post account move
        with self.registry.cursor() as cr:
            env = self.env(cr=cr)
            self.move.with_env(env).post()
            partner = self.partner.with_env(env)
            self.assertEqual(partner.supplier_rank, 0)
            self.assertEqual(partner.customer_rank, 1)

    def test_account_move_count_concurrent(self):
        # T2 Lock the partner row
        with self.registry.cursor() as cr:
            cr.execute("""SELECT id FROM res_partner WHERE id = %s FOR UPDATE""" % self.partner.id)

            # T3 concurrently posts account move and tries to update partner
            with self.registry.cursor() as cr:
                env = self.env(cr=cr)
                self.move.with_env(env).state = 'posted'

                self.assertEqual(self.partner.with_env(env).customer_rank,
                                 0, "It should not wait the concurrent transaction for the update")
