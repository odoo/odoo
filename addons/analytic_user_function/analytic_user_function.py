# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError


class analytic_user_funct_grid(osv.osv):
    _name = "analytic.user.funct.grid"
    _description = "Price per User"
    _rec_name = "user_id"
    _columns = {
        'user_id': fields.many2one("res.users", "User", required=True,),
        'product_id': fields.many2one("product.product", "Service", required=True,),
        'account_id': fields.many2one("account.analytic.account", "Analytic Account", required=True,),
        'uom_id': fields.related("product_id", "uom_id", relation="product.uom", string="Unit of Measure", type="many2one", readonly=True),
        'price': fields.float('Price', digits_compute=dp.get_precision('Product Price'), help="Price per hour for this user.", required=True),
    }

    def onchange_user_product_id(self, cr, uid, ids, user_id, product_id, context=None):
        if not user_id:
            return {}
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', user_id)], context=context)
        if not emp_id:
            return {}

        value = {}
        prod = False
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        emp = emp_obj.browse(cr, uid, emp_id[0], context=context)
        if emp.product_id and not product_id:
            value['product_id'] = emp.product_id.id
            prod = emp.product_id
        if prod:
            value['price'] = prod.list_price
            value['uom_id'] = prod.uom_id.id
        return {'value': value}


class account_analytic_account(osv.osv):
    _inherit = "account.analytic.account"
    _columns = {
        'user_product_ids': fields.one2many('analytic.user.funct.grid', 'account_id', 'Users/Products Rel.', copy=True),
    }


class account_analytic_line(osv.osv):
    _inherit = "account.analytic.line"

    # Look in account, if no value for the user => look in parent until there is no more parent to look
    # Take the first found... if nothing found => return False
    def _get_related_user_account_recursiv(self, cr, uid, user_id, account_id, context):
        user_function_id = self.pool.get('analytic.user.funct.grid').search(cr, uid, [('user_id', '=', user_id), ('account_id', '=', account_id)])
        account = self.pool['account.analytic.account'].browse(cr, uid, account_id)
        if user_function_id:
            return user_function_id
        elif account.parent_id:
            return self._get_related_user_account_recursiv(cr, uid, user_id, account.parent_id.id, context)
        else:
            return False

    def on_change_account_id(self, cr, uid, ids, account_id, user_id=False, unit_amount=0, is_timesheet=False, context=None):
        res = {}
        if not (account_id):
            return res
        if not (user_id):
            return super(account_analytic_line, self).on_change_account_id(cr, uid, ids, account_id, user_id, is_timesheet, context)

        # get the browse record related to user_id and account_id
        user_function_id = self._get_related_user_account_recursiv(cr, uid, user_id, account_id, context)
        if not user_function_id:
            # if there isn't any record for this user_id and account_id
            return super(account_analytic_line, self).on_change_account_id(cr, uid, ids, account_id, user_id, is_timesheet, context)
        else:
            # get the old values from super and add the value from the new relation analytic_user_funct_grid
            res['value'] = super(account_analytic_line, self).on_change_account_id(cr, uid, ids, account_id, user_id, is_timesheet, context)['value']
            res['value'].update(self._get_values_based_on_user_function(cr, uid, ids, user_function_id, unit_amount, context=context))
        return res

    def on_change_user_id(self, cr, uid, ids, user_id, unit_amount=0, account_id=None, is_timesheet=False, context=None):
        res = {}
        res = super(account_analytic_line, self).on_change_user_id(cr, uid, ids, user_id, is_timesheet, context=context)

        if account_id:
            # get the browse record related to user_id and account_id
            user_function_id = self._get_related_user_account_recursiv(cr, uid, user_id, account_id, context)
            if user_function_id:
                res['value'].update(self._get_values_based_on_user_function(cr, uid, ids, user_function_id, unit_amount, context=context))
        return res

    # Returns appropriate values for an analytic line if the user has a specific user_function
    def _get_values_based_on_user_function(self, cr, uid, ids, user_function_id, unit_amount=0, context=None):
        res = {}
        user_function = self.pool['analytic.user.funct.grid'].browse(cr, uid, user_function_id, context=context)
        product = user_function.product_id
        res['product_id'] = product.id
        res['uom_id'] = product.uom_id.id

        expense_account = product.property_account_expense_id.id
        if not expense_account:
            expense_account = product.categ_id.property_account_expense_categ_id.id
            if not expense_account:
                raise UserError(_('There is no expense account defined for this product: "%s" (id:%d)') % (product.name, product.id,))
        res['general_account_id'] = expense_account

        if unit_amount:
            new_amount = self.on_change_unit_amount(cr, uid, ids, product.id, unit_amount, False, product.uom_id.id)
            res['amount'] = new_amount['value']['amount']

        return res

    def _get_invoice_price(self, cr, uid, account, product_id, user_id, qty, context={}):
        for grid in account.user_product_ids:
            if grid.user_id.id == user_id:
                return grid.price
        return super(account_analytic_line, self)._get_invoice_price(cr, uid, account, product_id, user_id, qty, context)
