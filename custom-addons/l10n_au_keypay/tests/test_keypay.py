# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import os
from unittest import skipIf

from odoo.tests.common import tagged, TransactionCase


@tagged('external_l10n', 'external', 'post_install', '-at_install')
@skipIf(not os.getenv("KEYPAY_BUSINESS_ID" or not os.getenv("KEYPAY_API_KEY")), "no keypay credentials")
class TestKeypay(TransactionCase):
    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.KEYPAY_BUSINESS_ID = os.getenv("KEYPAY_BUSINESS_ID")
        cls.KEYPAY_API_KEY = os.getenv("KEYPAY_API_KEY")

        # Update address of company to Australia
        cls.company = cls.env.user.company_id
        cls.company.write({
            "street": "Bennelong Point",
            "city": "Sydney",
            "state_id": cls.env.ref("base.state_au_2").id,
            "country_id": cls.env.ref("base.au").id,
            "zip": "2000",
        })

        # Update config
        cls.config = cls.env["res.config.settings"].create({
            "l10n_au_kp_api_key": cls.KEYPAY_API_KEY,
            "l10n_au_kp_enable": True,
            "l10n_au_kp_identifier": cls.KEYPAY_BUSINESS_ID,
            "l10n_au_kp_lock_date": datetime.date(2023, 12, 31),
            "l10n_au_kp_journal_id": cls.env['account.journal'].search([
                ('code', '=', 'MISC'), ('company_id', '=', cls.company.id)
            ], limit=1).id,
        })
        cls.config.execute()

        Account = cls.env['account.account']

        # bis account should take priority as they have a kp_account_identifier
        Account.create([{
            'name': 'Test 1',
            'code': '1234',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 1 bis',
            'l10n_au_kp_account_identifier': '1234',
            'code': '9999',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 2 bis',
            'l10n_au_kp_account_identifier': '5678',
            'code': '8888',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 3',
            'code': 'abcd',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 4',
            'code': 'efgh',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 5',
            'code': 'ijkl',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 6',
            'code': 'mnop',
            'account_type': 'liability_current',
        }, {
            'name': 'Test 7',
            'code': 'qrst',
            'account_type': 'liability_current',
        }])

        Tax = cls.env['account.tax']
        cls.tax = Tax.create({
            'name': 'Test Tax 1',
            'amount': 10.0,
            'l10n_au_kp_tax_identifier': 'VAT1',
        })

        return res

    def test_01_keypay_fetch_payrun(self):
        # kp_lock_date is after all the entries no entries should be fetched
        self.config.action_kp_payroll_fetch_payrun()
        moves = self.env['account.move'].search([('l10n_au_kp_payrun_identifier', '!=', False)])
        self.assertEqual(len(moves), 0)

        # kp_lock_date is on the day of the first entry this one should not be fetched
        # there is more than a 100 payruns so this will do 2 calls to fetch everything
        self.company.write({"l10n_au_kp_lock_date": datetime.date(2020, 7, 31)})
        self.config.action_kp_payroll_fetch_payrun()
        moves = self.env['account.move'].search([('l10n_au_kp_payrun_identifier', '!=', False), ('date', '<=', datetime.date(2021, 7, 1))])
        self.assertEqual(len(moves), 17)

        # No kp_lock_date remaining entry should be fetched
        self.company.write({"l10n_au_kp_lock_date": False})
        self.config.action_kp_payroll_fetch_payrun()
        moves = self.env['account.move'].search([('l10n_au_kp_payrun_identifier', '!=', False), ('date', '<=', datetime.date(2021, 7, 1))])
        self.assertEqual(len(moves), 18)

        # verify if entries are correct
        self.assertEqual(len(moves[-2].line_ids), 5)
        self.assertEqual(len(moves[-1].line_ids), 5)
        self.assertEqual(moves[-2].date, datetime.date(2020, 8, 21))
        self.assertEqual(moves[-1].date, datetime.date(2020, 7, 31))
        self.assertEqual(moves[-2].line_ids.mapped('credit'), [1996.0, 0.0, 884.0, 0.0, 273.6])
        self.assertEqual(moves[-1].line_ids.mapped('credit'), [635.0, 0.0, 85.0, 0.0, 68.4])
        self.assertEqual(moves[-2].line_ids.mapped('debit'), [0.0, 2880.0, 0.0, 273.6, 0.0])
        self.assertEqual(moves[-1].line_ids.mapped('debit'), [0.0, 720.0, 0.0, 68.4, 0.0])
        # verify that bis account are used
        self.assertEqual(moves[-1].line_ids.mapped('account_id.name'), ['Test 2 bis', 'Test 1 bis', 'Test 4', 'Test 6', 'Test 7'])
        self.assertEqual(moves[-2].line_ids.mapped('account_id.name'), ['Test 2 bis', 'Test 1 bis', 'Test 4', 'Test 6', 'Test 7'])

    def test_02_keypay_fetch_payrun_with_tax(self):
        self.company.write({"l10n_au_kp_lock_date": datetime.date(2021, 8, 25)})

        self.config.action_kp_payroll_fetch_payrun()
        moves = self.env['account.move'].search([('l10n_au_kp_payrun_identifier', '!=', False), ('date', '<=', datetime.date(2021, 8, 31))])
        self.assertEqual(len(moves), 1)

        self.assertEqual(len(moves.line_ids), 3)
        self.assertEqual(moves.date, datetime.date(2021, 8, 26))
        self.assertEqual(moves.line_ids.mapped('credit'), [100.0, 0.0, 0.0])
        self.assertEqual(moves.line_ids.mapped('debit'), [0.0, 90.91, 9.09])
        self.assertEqual('Test Tax 1' in moves.line_ids.mapped('name'), True)
