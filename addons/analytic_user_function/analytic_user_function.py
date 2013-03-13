# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields,osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class analytic_user_funct_grid(osv.osv):
    _name="analytic.user.funct.grid"
    _description= "Price per User"
    _columns={
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
        'user_product_ids': fields.one2many('analytic.user.funct.grid', 'account_id', 'Users/Products Rel.'),
    }


class hr_analytic_timesheet(osv.osv):
    _inherit = "hr.analytic.timesheet"
    # Look in account, if no value for the user => look in parent until there is no more parent to look
    # Take the first found... if nothing found => return False
    def _get_related_user_account_recursiv(self, cr, uid, user_id, account_id):
        temp=self.pool.get('analytic.user.funct.grid').search(cr, uid, [('user_id', '=', user_id),('account_id', '=', account_id) ])
        account=self.pool.get('account.analytic.account').browse(cr, uid, account_id)
        if temp:
            return temp
        else:
            if account.parent_id:
                return self._get_related_user_account_recursiv(cr, uid, user_id, account.parent_id.id)
            else:
                return False

    def on_change_account_id(self, cr, uid, ids, account_id, user_id=False, unit_amount=0):
        res = {}
        if not (account_id):
            #avoid a useless call to super
            return res

        if not (user_id):
            return super(hr_analytic_timesheet, self).on_change_account_id(cr, uid, ids, account_id)

        #get the browse record related to user_id and account_id
        temp = self._get_related_user_account_recursiv(cr, uid, user_id, account_id)
        if not temp:
            #if there isn't any record for this user_id and account_id
            return super(hr_analytic_timesheet, self).on_change_account_id(cr, uid, ids, account_id)
        else:
            #get the old values from super and add the value from the new relation analytic_user_funct_grid
            r = self.pool.get('analytic.user.funct.grid').browse(cr, uid, temp)[0]
            res.setdefault('value',{})
            res['value']= super(hr_analytic_timesheet, self).on_change_account_id(cr, uid, ids, account_id)['value']
            res['value']['product_id'] = r.product_id.id
            res['value']['product_uom_id'] = r.product_id.uom_id.id

            #the change of product has to impact the amount, uom and general_account_id
            a = r.product_id.property_account_expense.id
            if not a:
                a = r.product_id.categ_id.property_account_expense_categ.id
            if not a:
                raise osv.except_osv(_('Error!'),
                        _('There is no expense account define ' \
                                'for this product: "%s" (id:%d)') % \
                                (r.product_id.name, r.product_id.id,))
            # Compute based on pricetype
            if unit_amount:
                amount_unit = self.on_change_unit_amount(cr, uid, ids,
                            r.product_id.id, unit_amount, False, r.product_id.uom_id.id)['value']['amount']
                amount = unit_amount *  amount_unit
                res ['value']['amount']= - round(amount, 2)
            res ['value']['general_account_id']= a
        return res

    def on_change_user_id(self, cr, uid, ids, user_id, account_id, unit_amount=0):
        res = super(hr_analytic_timesheet, self).on_change_user_id(cr, uid, ids, user_id)

        if account_id:
            #get the browse record related to user_id and account_id
            temp = self._get_related_user_account_recursiv(cr, uid, user_id, account_id)
            if temp:
                #add the value from the new relation analytic_user_funct_grid
                r = self.pool.get('analytic.user.funct.grid').browse(cr, uid, temp)[0]
                res['value']['product_id'] = r.product_id.id

                #the change of product has to impact the amount, uom and general_account_id
                a = r.product_id.property_account_expense.id
                if not a:
                    a = r.product_id.categ_id.property_account_expense_categ.id
                if not a:
                    raise osv.except_osv(_('Error!'),
                            _('There is no expense account define ' \
                                    'for this product: "%s" (id:%d)') % \
                                    (r.product_id.name, r.product_id.id,))
                # Compute based on pricetype
                if unit_amount:
                    amount_unit = self.on_change_unit_amount(cr, uid, ids,
                        r.product_id.id, unit_amount, False, r.product_id.uom_id.id)['value']['amount']

                    amount = unit_amount * amount_unit
                    res ['value']['amount']= - round(amount, 2)
                res ['value']['general_account_id']= a
        return res

class account_analytic_line(osv.osv):
    _inherit = "account.analytic.line"
    def _get_invoice_price(self, cr, uid, account, product_id, user_id, qty, context = {}):
        for grid in account.user_product_ids:
            if grid.user_id.id==user_id:
                return grid.price
        return super(account_analytic_line, self)._get_invoice_price(cr, uid, account, product_id, user_id, qty, context)

