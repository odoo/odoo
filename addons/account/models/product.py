# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_income_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account", oldname="property_account_income_categ",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value sales.")
    property_account_expense_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account", oldname="property_account_expense_categ",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices to value expenses.")

#----------------------------------------------------------
# Products
#----------------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = "product.template"

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', string='Customer Taxes',
        domain=[('type_tax_use', '=', 'sale')])
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id', string='Vendor Taxes',
        domain=[('type_tax_use', '=', 'purchase')])
    property_account_income_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account", oldname="property_account_income",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices instead of the default one to value sales for the current product.")
    property_account_expense_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account", oldname="property_account_expense",
        domain=[('deprecated', '=', False)],
        help="This account will be used for invoices instead of the default one to value expenses for the current product.")

    @api.multi
    def write(self, vals):
        #TODO: really? i don't see the reason we'd need that constraint..
        check = self.ids and 'uom_po_id' in vals
        if check:
            self._cr.execute("SELECT id, uom_po_id FROM product_template WHERE id IN %s", [tuple(self.ids)])
            uoms = dict(self._cr.fetchall())
        res = super(ProductTemplate, self).write(vals)
        if check:
            self._cr.execute("SELECT id, uom_po_id FROM product_template WHERE id IN %s", [tuple(self.ids)])
            if dict(self._cr.fetchall()) != uoms:
                products = self.env['product.product'].search([('product_tmpl_id', 'in', self.ids)])
                if self.env['account.move.line'].search_count([('product_id', 'in', products.ids)]):
                    raise UserError(_('You can not change the unit of measure of a product that has been already used in an account journal item. If you need to change the unit of measure, you may deactivate this product.'))
        return res

    @api.multi
    def _get_product_accounts(self):
        return {
            'income': self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        }

    @api.multi
    def _get_asset_accounts(self):
        res = {}
        res['stock_input'] = False
        res['stock_output'] = False
        return res

    @api.multi
    def get_product_accounts(self, fiscal_pos=None):
        accounts = self._get_product_accounts()
        if not fiscal_pos:
            fiscal_pos = self.env['account.fiscal.position']
        return fiscal_pos.map_accounts(accounts)
