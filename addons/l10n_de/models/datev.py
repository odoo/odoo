from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_de_datev_code = fields.Char(size=4, help="4 digits code use by Datev", tracking=True)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_product_accounts(self):
        """ As taxes with a different rate need a different income/expense account, we add this logic in case people only use
         invoicing to not be blocked by the above constraint"""
        result = super(ProductTemplate, self)._get_product_accounts()
        company = self.env.company
        if company.account_fiscal_country_id.code == "DE":
            if not self.property_account_income_id:
                taxes = self.taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(company))
                if not result['income'] or (result['income'].tax_ids and taxes and taxes[0] not in result['income'].tax_ids):
                    result_income = self.env['account.account'].search([
                        *self.env['account.account']._check_company_domain(company),
                        ('internal_group', '=', 'income'),
                        ('deprecated', '=', False),
                        ('tax_ids', 'in', taxes.ids)
                    ], limit=1)
                    result['income'] = result_income or result['income']
            if not self.property_account_expense_id:
                supplier_taxes = self.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(company))
                if not result['expense'] or (result['expense'].tax_ids and supplier_taxes and supplier_taxes[0] not in result['expense'].tax_ids):
                    result_expense = self.env['account.account'].search([
                        *self.env['account.account']._check_company_domain(company),
                        ('internal_group', '=', 'expense'),
                        ('deprecated', '=', False),
                        ('tax_ids', 'in', supplier_taxes.ids),
                    ], limit=1)
                    result['expense'] = result_expense or result['expense']
        return result
