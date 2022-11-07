# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tests.common import users

@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    @users('admin')
    def test_01_account_tour(self):
        # For some l10n modules some required data are needed to complete the tour.
        # e.g. l10n_mx_edi required some certificates files to be upload and set on the company.
        # Since (most of the time) the extra data are added to a new company
        # (except for the country_id field that might be changed on the main company
        # but not account_fiscal_country_id), to maximise the chance to have a fully
        # configured company, we chose the one that have the same country as fiscal country.
        if self.env.company.country_id != self.env.company.account_fiscal_country_id:
            country_id = self.env.company.account_fiscal_country_id or self.env.company.country_id
            company = self.env.user.company_ids.filtered(lambda c: c.country_id.id == c.account_fiscal_country_id.id == country_id.id)
            if company:
                self.env.company = company[0]
                self.env.user.company_id = company[0]
        # This tour doesn't work with demo data on runbot
        all_moves = self.env['account.move'].search([('move_type', '!=', 'entry')])
        all_moves.button_draft()
        all_moves.with_context(force_delete=True).unlink()
        self.start_tour("/web", 'account_tour', login="admin")
