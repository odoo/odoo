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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class product_category(osv.osv):
    _inherit = "product.category"
    _columns = {
        'property_account_income_categ': fields.property(
            type='many2one',
            relation='account.account',
            string="Income Account",
            help="This account will be used for invoices to value sales."),
        'property_account_expense_categ': fields.property(
            type='many2one',
            relation='account.account',
            string="Expense Account",
            help="This account will be used for invoices to value expenses."),
    }

#----------------------------------------------------------
# Products
#----------------------------------------------------------

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'taxes_id': fields.many2many('account.tax', 'product_taxes_rel',
            'prod_id', 'tax_id', 'Customer Taxes',
            domain=[('parent_id','=',False),('type_tax_use','in',['sale','all'])]),
        'supplier_taxes_id': fields.many2many('account.tax',
            'product_supplier_taxes_rel', 'prod_id', 'tax_id',
            'Supplier Taxes', domain=[('parent_id', '=', False),('type_tax_use','in',['purchase','all'])]),
        'property_account_income': fields.property(
            type='many2one',
            relation='account.account',
            string="Income Account",
            help="This account will be used for invoices instead of the default one to value sales for the current product."),
        'property_account_expense': fields.property(
            type='many2one',
            relation='account.account',
            string="Expense Account",
            help="This account will be used for invoices instead of the default one to value expenses for the current product."),
    }

    def write(self, cr, uid, ids, vals, context=None):
        check = ids and 'uom_po_id' in vals
        if check:
            cr.execute("SELECT id, uom_po_id FROM product_template WHERE id IN %s", [tuple(ids)])
            uoms = dict(cr.fetchall())

        result = super(product_template, self).write(cr, uid, ids, vals, context=context)

        if check:
            cr.execute("SELECT id, uom_po_id FROM product_template WHERE id IN %s", [tuple(ids)])
            if dict(cr.fetchall()) != uoms:
                product_ids = self.pool['product.product'].search(cr, uid, [('product_tmpl_id', 'in', ids)], context=context)
                if self.pool['account.move.line'].search_count(cr, uid, [('product_id', 'in', product_ids)], context=context):
                    raise UserError(_("You can not change the unit of measure of a product that has been already used in an account journal item. If you need to change the unit of measure, you may deactivate this product."))
        return result
