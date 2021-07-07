# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

ACCOUNT_DOMAIN = "['&', '&', '&', ('deprecated', '=', False), ('internal_type','=','other'), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"

class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_income_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="This account will be used when validating a customer invoice.")
    property_account_expense_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.")

#----------------------------------------------------------
# Products
#----------------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_default_taxes_id(self):
        if self.company_id:
            return self.company_id.account_sale_tax_id
        return self.default_tax_by_allowed_companies()

    def _get_default_supplier_taxes_id(self):
        if self.company_id:
            return self.company_id.account_purchase_tax_id
        return self.default_tax_by_allowed_companies(is_sales_tax=False)

    def default_tax_by_allowed_companies(self, is_sales_tax=True, forcefully=False):
        company_ids = self.sudo().env['res.company'].search([])
        if not forcefully and self.env.context.get('allowed_company_ids'):
            company_ids = company_ids.filtered(lambda c: c.id in self.env.context.get('allowed_company_ids'))
        if is_sales_tax:
            return company_ids.sudo().mapped('account_sale_tax_id')
        return company_ids.sudo().mapped('account_purchase_tax_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals['taxes_id'][0][2] == self.default_tax_by_allowed_companies().ids:
                vals['taxes_id'] = [[6, 0, self.default_tax_by_allowed_companies(forcefully=True).ids]]
            if vals['supplier_taxes_id'][0][2] == self.default_tax_by_allowed_companies(is_sales_tax=False).ids:
                vals['supplier_taxes_id'] = [[6, 0, self.default_tax_by_allowed_companies(is_sales_tax=False, forcefully=True).ids]]
        templates = super(ProductTemplate, self).create(vals_list)
        return templates

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.taxes_id = self.company_id.account_sale_tax_id
            self.supplier_taxes_id = self.company_id.account_purchase_tax_id
        else:
            self.taxes_id = self.default_tax_by_allowed_companies()
            self.supplier_taxes_id = self.default_tax_by_allowed_companies(is_sales_tax=False)

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', help="Default taxes used when selling the product.", string='Customer Taxes',
        domain=[('type_tax_use', '=', 'sale')], default=_get_default_taxes_id)
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id', string='Vendor Taxes', help='Default taxes used when buying the product.',
        domain=[('type_tax_use', '=', 'purchase')], default=_get_default_supplier_taxes_id)
    property_account_income_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category.")
    property_account_expense_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")

    def _get_product_accounts(self):
        return {
            'income': self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        }

    def _get_asset_accounts(self):
        res = {}
        res['stock_input'] = False
        res['stock_output'] = False
        return res

    def get_product_accounts(self, fiscal_pos=None):
        accounts = self._get_product_accounts()
        if not fiscal_pos:
            fiscal_pos = self.env['account.fiscal.position']
        return fiscal_pos.map_accounts(accounts)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_product_accounts(self):
        return self.product_tmpl_id._get_product_accounts()
