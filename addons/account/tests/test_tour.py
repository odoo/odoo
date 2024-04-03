# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(AccountTestInvoicingCommon, odoo.tests.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        all_moves = cls.env['account.move'].search([('move_type', '!=', 'entry')])
        all_moves.button_draft()
        all_moves.with_context(force_delete=True).unlink()

        # In case of latam impacting multiple countries, disable the required fields manually.
        if 'l10n_latam_use_documents' in cls.env['account.journal']._fields:
            cls.env['account.journal']\
                .search([('company_id', '=', cls.env.company.id), ('type', '=', 'purchase')])\
                .write({'l10n_latam_use_documents': False})

    def test_01_account_tour(self):
        # Reset country and fiscal country, so that fields added by localizations are
        # hidden and non-required, and don't make the tour crash.
        # Also remove default taxes from the company and its accounts, to avoid inconsistencies
        # with empty fiscal country.
        self.env.ref('base.user_admin').write({
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
        })
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

    def test_01_account_tax_groups_tour(self):
        self.env.ref('base.user_admin').write({
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
        })
        self.env['res.partner'].create({
            'name': 'Account Tax Group Partner',
            'email': 'azure.Interior24@example.com',
        })
        product = self.env['product.product'].create({
            'name': 'Account Tax Group Product',
            'standard_price': 600.0,
            'list_price': 147.0,
            'detailed_type': 'consu',
        })
        new_tax = self.env['account.tax'].create({
            'name': '10% Tour Tax',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
        })
        product.supplier_taxes_id = new_tax

        self.start_tour("/web", 'account_tax_group', login="admin")
