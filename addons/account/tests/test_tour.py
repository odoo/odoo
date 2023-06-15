# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
import odoo.tests


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_account_tour(self):
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
        # This tour doesn't work with demo data on runbot
        all_moves = self.env['account.move'].search([('move_type', '!=', 'entry')])
        all_moves.button_draft()
        all_moves.with_context(force_delete=True).unlink()

        # In case of latam impacting multiple countries, disable the required fields manually.
        if 'l10n_latam_use_documents' in self.env['account.journal']._fields:
            self.env['account.journal']\
                .search([('company_id', '=', self.env.company.id), ('type', '=', 'sale')])\
                .write({'l10n_latam_use_documents': False})

        self.start_tour("/web", 'account_tour', login="admin")

    def test_01_account_tax_groups_tour(self):
        self.start_tour("/web", 'account_tax_group', login="admin")
