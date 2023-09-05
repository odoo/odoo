# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
import odoo.tests


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        all_moves = cls.env['account.move'].search([('move_type', '!=', 'entry')])
        all_moves = all_moves.filtered(lambda m: not m.inalterable_hash and m.state in ('posted', 'cancel'))
        # This field is only present in account_accountant
        if 'deferred_move_ids' in all_moves._fields:
            all_moves = all_moves.filtered(lambda m: not m.deferred_move_ids)
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
        self.env.company.write({
            'country_id': None, # Also resets account_fiscal_country_id
            'account_sale_tax_id': None,
            'account_purchase_tax_id': None,
        })

        account_with_taxes = self.env['account.account'].search([('tax_ids', '!=', False), ('company_id', '=', self.env.company.id)])
        account_with_taxes.write({
            'tax_ids': [Command.clear()],
        })

        # Remove all posted invoices to enable 'create first invoice' button
        invoices = self.env['account.move'].search([('company_id', '=', self.env.company.id), ('move_type', '=', 'out_invoice')])
        for invoice in invoices:
            if invoice.state in ('cancel', 'posted'):
                invoice.button_draft()
        invoices.unlink()

        self.start_tour("/web", 'account_tour', login="admin")

    def test_01_account_tax_groups_tour(self):
        product = self.env.ref('product.product_product_5')
        company_used = self.env.companies.sorted(lambda c: c.id)[0]
        new_tax = self.env['account.tax'].create({
            'name': '10% Tour Tax',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
            'company_id': company_used.id,
            'country_id': company_used.account_fiscal_country_id.id
        })
        product.supplier_taxes_id = new_tax

        self.start_tour("/web", 'account_tax_group', login="admin")
