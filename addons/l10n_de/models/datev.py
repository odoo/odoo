from odoo import fields, models

class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_de_datev_code = fields.Char(size=4)

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        vals['l10n_de_datev_code'] = self.l10n_de_datev_code
        return vals

class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_de_datev_code = fields.Char(size=4, help="4 digits code use by Datev")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_product_accounts(self):
        """ As taxes with a different rate need a different income/expense account, we add this logic in case people only use
         invoicing to not be blocked by the above constraint"""
        result = super(ProductTemplate, self)._get_product_accounts()
        company = self.env.company
        if company.account_fiscal_country_id.code == "DE":
            if not self.property_account_income_id:
                taxes = self.taxes_id.filtered(lambda t: t.company_id == company)
                if not result['income'] or (result['income'].tax_ids and taxes and taxes[0] not in result['income'].tax_ids):
                    result['income'] = self.env['account.account'].search([('internal_group', '=', 'income'), ('deprecated', '=', False),
                                                                   ('tax_ids', 'in', taxes.ids)], limit=1)
            if not self.property_account_expense_id:
                supplier_taxes = self.supplier_taxes_id.filtered(lambda t: t.company_id == company)
                if not result['expense'] or (result['expense'].tax_ids and supplier_taxes and supplier_taxes[0] not in result['expense'].tax_ids):
                    result['expense'] = self.env['account.account'].search([('internal_group', '=', 'expense'), ('deprecated', '=', False),
                                                                   ('tax_ids', 'in', supplier_taxes.ids)], limit=1)
        return result
