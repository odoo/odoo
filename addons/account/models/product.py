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

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', help="Default taxes used when selling the product.", string='Customer Taxes',
        domain=[('type_tax_use', '=', 'sale')],
        compute='_compute_taxes', store=True, readonly=False)
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id', string='Vendor Taxes', help='Default taxes used when buying the product.',
        domain=[('type_tax_use', '=', 'purchase')],
        compute='_compute_taxes', store=True, readonly=False)
    property_account_income_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category.")
    property_account_expense_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")

    @api.depends('company_id')
    def _compute_taxes(self):
        for product in self:
            if product.company_id:
                product.taxes_id = product.company_id.account_purchase_tax_id
                product.supplier_taxes_id = product.company_id.account_sale_tax_id
            else:
                sales_taxes, supplier_taxes = self._get_default_taxes(only_allowed_companies=True)
                product.taxes_id = sales_taxes
                product.supplier_taxes_id = supplier_taxes

    @api.model
    def _get_default_taxes(self, only_allowed_companies=False):
        allowed_company_ids = self.env.context.get('allowed_company_ids') or self.env.company.ids
        operator = 'in' if only_allowed_companies else 'not in'
        companies = self.env['res.company'].sudo().search([('id', operator, allowed_company_ids)])
        return companies.mapped('account_sale_tax_id'), companies.mapped('account_purchase_tax_id')

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

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        # check allowed company to avoid the test case access
        for product in products.filtered(lambda l: not l.company_id):
            sale_taxes, supplier_taxes = product._get_default_taxes()
            if sale_taxes:
                product.sudo().write({'taxes_id': [(4, tx) for tx in sale_taxes.ids]})
            if supplier_taxes:
                product.sudo().write({'supplier_taxes_id': [(4, tx) for tx in supplier_taxes.ids]})
        return products


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_product_accounts(self):
        return self.product_tmpl_id._get_product_accounts()
