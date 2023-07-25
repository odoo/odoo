from odoo.tests.common import TransactionCase

class TestWebsiteSaleCommon(TransactionCase):

    def setUp(self):
        super(TestWebsiteSaleCommon, self).setUp()
        # Reset country and fiscal country, so that fields added by localizations are
        # hidden and non-required.
        # Also remove default taxes from the company and its accounts, to avoid inconsistencies
        # with empty fiscal country.
        self.env.company.write({
            'country_id': None, # Also resets account_fiscal_country_id
            'account_sale_tax_id': None,
            'account_purchase_tax_id': None,
        })
        account_with_taxes = self.env['account.account'].search([('tax_ids', '!=', False), ('company_id', '=', self.env.company.id)])
        account_with_taxes.write({
            'tax_ids': [(5, 0, 0)],
        })
        # Update website pricelist to ensure currency is same as env.company
        website = self.env['website'].get_current_website()
        pricelist = website.get_current_pricelist()
        pricelist.write({'currency_id': self.env.company.currency_id.id})
