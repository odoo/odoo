# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
import odoo.tests


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_account_tour(self):
        # This tour doesn't work with demo data on runbot
        all_moves = self.env['account.move'].search([('move_type', '!=', 'entry')])
        all_moves.button_draft()
        all_moves.with_context(force_delete=True).unlink()

        Journal = self.env['account.journal']
        journal_ids = Journal.search([('company_id', '=', self.env.company.id)])
        journal_ids.write({'active': False})
        # Since demo data removed/archived, must add a Sale Journal to make the tour work
        Journal.create({
            'name': 'test_out_invoice_journal',
            'code': 'XXXXX',
            'type': 'sale',
            'company_id':  self.env.company.id,
        })

        # Reset country and fiscal country, so that fields added by localizations are
        # hidden and non-required, and don't make the tour crash.
        # Also remove default taxes from the company and its accounts, to avoid inconsistencies
        # with empty fiscal country.
        self.env.company.write({
            'country_id': None, # Also resets account_fiscal_country_id
            'account_sale_tax_id': None,
            'account_purchase_tax_id': None,
        })
        account_with_taxes = self.env['account.account'].search([('tax_ids', '!=', False), ('company_id', '=', self.env.company.id)])
        account_with_taxes.write({
            'tax_ids': [Command.clear()],
        })

        self.start_tour("/web", 'account_tour', login="admin")
