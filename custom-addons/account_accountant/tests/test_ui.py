# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command
import odoo.tests

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('-at_install', 'post_install')
class TestUi(odoo.tests.HttpCase):
    def test_accountant_tour(self):
        # Reset country and fiscal country, so that fields added by localizations are
        # hidden and non-required, and don't make the tour crash.
        # Also remove default taxes from the company and its accounts, to avoid inconsistencies
        # with empty fiscal country.
        if not odoo.tests.loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.env.company.write({
            'country_id': None,  # Also resets account_fiscal_country_id
            'account_sale_tax_id': None,
            'account_purchase_tax_id': None,
        })

        account_with_taxes = self.env['account.account'].search([('tax_ids', '!=', False), ('company_id', '=', self.env.company.id)])
        account_with_taxes.write({
            'tax_ids': [Command.clear()],
        })
        # This tour doesn't work with demo data on runbot
        all_moves = self.env['account.move'].search([('move_type', '!=', 'entry')])
        all_moves.filtered(lambda m: not m.inalterable_hash and not m.deferred_move_ids and m.state != 'draft').button_draft()
        all_moves.with_context(force_delete=True).unlink()
        self.start_tour("/web", 'account_accountant_tour', login="admin")
