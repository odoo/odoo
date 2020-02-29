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
                'move_type': 'out_invoice',
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
