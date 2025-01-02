# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html
from freezegun import freeze_time
from datetime import datetime, timedelta

from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tools import mute_logger
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestAccountDigest(TestDigestCommon):

    @classmethod
    @mute_logger('odoo.models.unlink')
    def setUpClass(cls):
        super().setUpClass()
        account1 = cls.env['account.account'].search([('internal_group', '=', 'income'), ('company_id', '=', cls.company_1.id)], limit=1)
        account2 = cls.env['account.account'].search([('internal_group', '=', 'expense'), ('company_id', '=', cls.company_1.id)], limit=1)
        cls.env['account.journal'].with_company(cls.company_2).create({
            'name': 'Test Journal',
            'code': 'code',
            'type': 'general',
        })

        comp2_account, comp2_account2 = cls.env['account.account'].create([{
            'name': 'Account 1 Company 2',
            'account_type': 'expense_depreciation',
            'company_id': cls.company_2.id,
            'code': 'aaaaaa',
        }, {
            'name': 'Account 2 Company 2',
            'account_type': 'income_other',
            'company_id': cls.company_2.id,
            'code': 'bbbbbb',
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

    @freeze_time("2025-01-30")
    def test_kpi_currency_follows_recipients_company_currency(self):
        """ Ensure that in the following setup EU Recipient receives a digest in his currency.

           ODOO two company setup
         ┌────────────┌────────────────┐
         │ US Branch  │   EU Branch    │
         │   $$$      │     €€€        │
         │            │                │
         │   Sales    │                │
         │            │                │
         │ US Digest ─├─►EU Recipient │
         │            │                │
         └────────────└────────────────┘
        """
        def _record_revenue(for_amount=100, when='in '):
            if when == 'in past 24h':
                move_date = datetime.now().strftime('%Y-%m-%d')
            elif when == 'in past week':
                move_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            elif when == 'in past month':
                move_date = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
            else:
                move_date = when  # Assume it's a valid date string in 'YYYY-MM-DD' format

            move = self.env['account.move'].with_company(us_branch).create({
                'date': move_date,
                'line_ids': [
                    Command.create({
                        'account_id': income_account.id,
                        'credit': for_amount,
                    }),
                    Command.create({
                        'account_id': receivable_account.id,
                        'debit': for_amount,
                    }),
                ],
            })
            move.action_post()
            return move

        eu_currency = self.env['res.currency'].create({
            'name': 'eu_currency',
            'symbol': '€€€',
            'rounding': 0.01,
            'decimal_places': 2,
        })

        eu_branch = self.env['res.company'].create({'name': 'eu_branch', 'currency_id': eu_currency.id})

        eu_recipient = self.env['res.users'].create({
            'name': 'eu_recipient',
            'login': 'eu_recipient@example.com',
            'email': 'eu_recipient@example.com',
            'company_id': eu_branch.id,
            'company_ids': [(4, eu_branch.id)],
            'groups_id': [
                Command.set([self.env.ref('base.group_user').id]),
                Command.set([self.env.ref('account.group_account_invoice').id]),
            ]
        })

        us_currency = self.env['res.currency'].create({
            'name': 'us_currency',
            'symbol': '$$$',
            'rounding': 0.01,
            'decimal_places': 2,
        })

        self.env['res.currency.rate'].create({
            'name': '2025-01-01',
            'currency_id': us_currency.id,
            'rate': 0.5,
            'company_id': eu_branch.id,
        })

        us_branch = self.env['res.company'].create({'name': 'us_branch', 'currency_id': us_currency.id})

        us_digest = self.env['digest.digest'].with_company(us_branch).create({
            'name': 'Test Digest',
            'user_ids': [(4, eu_recipient.id)],
            'kpi_account_total_revenue': True,  # Enable the revenue KPI
        })

        income_account = self.env['account.account'].create({
            'name': 'Income Account',
            'code': '400000',
            'account_type': 'income',
            'company_id': us_branch.id,
        })
        receivable_account = self.env['account.account'].create({
            'name': 'Receivable Account',
            'account_type': 'asset_receivable',
            'code': '1210',
            'company_id': us_branch.id,
        })
        self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'general',
            'code': 'TJ',
            'company_id': us_branch.id,
        })

        _record_revenue(for_amount=1, when='in past 24h')  # =2€€€ cumulatively
        _record_revenue(for_amount=9, when='in past week')  # =20€€€ cumulatively
        _record_revenue(for_amount=90, when='in past month')  # =200€€€ cumulatively

        self.env['account.move.line'].flush_model()

        us_digest.flush_recordset()
        with self.mock_mail_gateway():
            us_digest.action_send()

        self.assertEqual(len(self._new_mails), 1, "A new mail.mail should have been created")
        mail = self._new_mails[0]
        self.assertEqual(mail.email_to, eu_recipient.email_formatted)

        kpi_xpath = '//span[contains(@class, "kpi_value") and contains(@class, "kpi_border_col")]/text()'
        kpi_message_values = html.fromstring(mail.body_html).xpath(kpi_xpath)

        self.assertEqual(
            [t.strip() for t in kpi_message_values],
            ['2€€€', '20€€€', '200€€€'],
            "The digest should display the KPI values in the recipient's company currency"
        )
