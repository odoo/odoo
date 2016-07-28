# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import UserError

class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_sales_discount_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Sales Discount Account", 
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value sales discount.")
    property_account_sales_return_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Sales Return Account", 
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value sales return.")

#----------------------------------------------------------
# Products
#----------------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_account_sales_discount_id = fields.Many2one('account.account', company_dependent=True,
        string="Sales Discount Account", 
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value sales discount.")
    property_account_sales_return_id = fields.Many2one('account.account', company_dependent=True,
        string="Sales Return Account", 
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value sales return.")
    

    @api.multi
    def _get_product_accounts(self):
        return {
            'sales_discount': self.property_account_sales_discount_id or self.categ_id.property_account_sales_discount_categ_id,
            'sales_return': self.property_account_sales_return_id or self.categ_id.property_account_sales_return_categ_id
        }