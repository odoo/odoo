# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestMockOnlineSyncCommon
import odoo.tests

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('-at_install', 'post_install')
class TestUi(AccountTestMockOnlineSyncCommon):
    def test_accountant_tour(self):
        # Reset country and fiscal country, so that fields added by localizations are
        # hidden and non-required, and don't make the tour crash.
        # Also remove default taxes from the company and its accounts, to avoid inconsistencies
        # with empty fiscal country.
        self.env.company.write({
            'country_id': None,  # Also resets account_fiscal_country_id
            'account_sale_tax_id': None,
            'account_purchase_tax_id': None,
        })

        # An unconfigured bank journal is required for the connect bank step
        self.env['account.journal'].create({
            'type': 'bank',
            'name': 'Empty Bank',
            'code': 'EBJ',
        })

        account_with_taxes = self.env['account.account'].search([('tax_ids', '!=', False), ('company_ids', '=', self.env.company.id)])
        account_with_taxes.write({
            'tax_ids': [Command.clear()],
        })
        # This tour doesn't work with demo data on runbot
        all_moves = self.env['account.move'].search([('company_id', '=', self.env.company.id), ('move_type', '!=', 'entry')])
        all_moves.filtered(lambda m: not m.inalterable_hash and not m.deferred_move_ids and m.state != 'draft').button_draft()
        all_moves.with_context(force_delete=True).unlink()
        # We need at least two bank statement lines to reconcile for the tour.
        bnk = self.env['account.account'].create({
            'code': 'X1014',
            'name': 'Bank Current Account - (test)',
            'account_type': 'asset_cash',
        })
        journal = self.env['account.journal'].create({
            'name': 'Bank - Test',
            'code': 'TBNK',
            'type': 'bank',
            'default_account_id': bnk.id,
        })
        self.env['account.bank.statement.line'].create([{
            'journal_id': journal.id,
            'amount': 100,
            'date': fields.Date.today(),
            'payment_ref': 'stl_0001',
        }, {
            'journal_id': journal.id,
            'amount': 200,
            'date': fields.Date.today(),
            'payment_ref': 'stl_0002',
        }])
        self.start_tour("/odoo", 'account_accountant_tour', login="admin")
