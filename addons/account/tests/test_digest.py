# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tools import mute_logger
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountDigest(TestDigestCommon):

    @classmethod
    @mute_logger('odoo.models.unlink')
    def setUpClass(cls):
        super().setUpClass()
        account1 = cls.env['account.account'].search([('internal_group', '=', 'income'), ('company_ids', '=', cls.company_1.id)], limit=1)
        account2 = cls.env['account.account'].search([('internal_group', '=', 'expense'), ('company_ids', '=', cls.company_1.id)], limit=1)
        cls.env['account.journal'].with_company(cls.company_2).create({
            'name': 'Test Journal',
            'code': 'code',
            'type': 'general',
        })

        comp2_account, comp2_account2 = cls.env['account.account'].create([{
            'name': 'Account 1 Company 2',
            'account_type': 'expense_depreciation',
            'code': 'aaaaaa',
            'company_ids': [Command.link(cls.company_2.id)],
        }, {
            'name': 'Account 2 Company 2',
            'account_type': 'income_other',
            'code': 'bbbbbb',
            'company_ids': [Command.link(cls.company_2.id)],
        }])

        cls.env['account.move'].search([]).state = 'draft'

        moves = cls.env['account.move'].create({
            'line_ids': [
                (0, 0, {'debit': 5, 'credit': 0, 'account_id': account1.id}),
                (0, 0, {'debit': 0, 'credit': 5, 'account_id': account2.id}),
                (0, 0, {'debit': 8, 'credit': 0, 'account_id': account1.id}),
                (0, 0, {'debit': 0, 'credit': 8, 'account_id': account2.id}),
            ],
        })

        moves |= cls.env['account.move'].with_company(cls.company_2).create({
            'line_ids': [
                (0, 0, {'debit': 0, 'credit': 2, 'account_id': comp2_account.id}),
                (0, 0, {'debit': 2, 'credit': 0, 'account_id': comp2_account2.id}),
            ],
        })

        moves.state = 'posted'

    def test_kpi_account_total_revenue_value(self):
        self.assertEqual(int(self.digest_1.kpi_account_total_revenue_value), -13)
        self.assertEqual(int(self.digest_2.kpi_account_total_revenue_value), -2)
        self.assertEqual(int(self.digest_3.kpi_account_total_revenue_value), -13)

        self.digest_3.invalidate_recordset()
        self.assertEqual(
            int(self.digest_3.with_company(self.company_2).kpi_account_total_revenue_value),
            -2,
            msg='When no company is set, the KPI must be computed based on the current company',
        )
