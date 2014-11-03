# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import Warning

class product_category(models.Model):
    _inherit = "product.category"

    property_account_income_categ = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value sales.")
    property_account_expense_categ = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value expenses.")


#----------------------------------------------------------
# Products
#----------------------------------------------------------

class product_template(models.Model):
    _inherit = "product.template"

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', string='Customer Taxes',
        domain=[('parent_id', '=', False), ('type_tax_use', 'in', ['sale', 'all'])])
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id', string='Supplier Taxes',
        domain=[('parent_id', '=', False), ('type_tax_use', 'in', ['purchase', 'all'])])
    property_account_income = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices instead of the default one to value sales for the current product.")
    property_account_expense = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices instead of the default one to value expenses for the current product.")

    @api.multi
    def write(self, vals):
        if 'uom_po_id' in vals:
            products = self.env['product.product'].search([('product_tmpl_id', 'in', ids)])
            if self.env['account.move.line'].search([('product_id', 'in', products.ids)], limit=1):
                raise Warning(_('You can not change the unit of measure of a product that has been already used in an account journal item. If you need to change the unit of measure, you may deactivate this product.'))
        return super(product_template, self).write(vals)
