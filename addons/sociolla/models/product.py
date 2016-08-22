from openerp.osv import fields, osv
from openerp import api, fields, models, _
from openerp.exceptions import UserError

class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_sales_discount_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Sales Discount",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value sales discount.")
    property_account_sales_return_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Sales Return", 
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value sales return.")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_account_sales_discount_id = fields.Many2one('account.account', company_dependent=True,
        string="Sales Discount",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices instead of the default one to value sales discount for the current product.")
    property_account_sales_return_id = fields.Many2one('account.account', company_dependent=True,
        string="Sales Return", 
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices instead of the default one to value sales return for the current product.")

    @api.multi
    def _get_asset_accounts(self):
        res = super(ProductTemplate, self)._get_asset_accounts()
        res['sales_discount'] = False
        res['sales_return'] = False
        return res

class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'

    @api.multi
    def _get_product_accounts(self):
        """ Add the sales discount, sales return related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super(product_template, self)._get_product_accounts()
        res = self._get_asset_accounts()
        accounts.update({
            'sales_discount': res['sales_discount'] or self.property_account_sales_discount_id or self.categ_id.property_account_sales_discount_categ_id,
            'sales_return': res['sales_return'] or self.property_account_sales_return_id or self.categ_id.property_account_sales_return_categ_id,
        })
        return accounts