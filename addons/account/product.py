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

class product_product(osv.osv):
    _inherit = "product.product"
    
    def _check_coa_configured(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        prop_ids = self.pool.get('ir.property').search(cr, uid, [('name','in',('property_account_income', 'property_account_income_categ', 'property_account_expense', 'property_account_expense_categ')),(('company_id', '=', company_id) or ('company_id', '=', False))], context=context)
        return bool(prop_ids)
   
    def _get_coa_configured(self, cr, uid, ids, field_names, arg, context=None):
        return dict.fromkeys(ids, self._check_coa_configured(cr, uid, context=context)) 
    
    def open_account_configuration_installer(self, cr, uid, ids, context=None):
        return self.pool.get('account.installer')._open_account_configuration_installer(cr, uid, ids, context=context)
    
    _columns = {
        'is_coa_configured': fields.function(_get_coa_configured, type='boolean', string='COA Configured',
            store={
                'product.product': (lambda self, cr, uid, ids, c={}: ids, ['property_account_income', 'property_account_expense'], 50),
            },),
    }
    _defaults = {
        'is_coa_configured': _check_coa_configured,
    }
    
class product_category(osv.osv):
    _inherit = "product.category"
    
    def _check_coa_configured(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        prop_ids = self.pool.get('ir.property').search(cr, uid, [('name', 'in', ('property_account_income_categ', 'property_account_expense_categ')), (('company_id', '=', company_id) or ('company_id', '=', False))], context=context)
        return bool(prop_ids) 
    
    def _get_coa_configured(self, cr, uid, ids, field_names, arg, context=None):
        return dict.fromkeys(ids, self._check_coa_configured(cr, uid, context=context)) 
    
    def open_account_configuration_installer(self, cr, uid, ids, context=None):
        return self.pool.get('account.installer')._open_account_configuration_installer(cr, uid, ids, context=context)
    
    _columns = {
        'is_coa_configured': fields.function(_get_coa_configured, type='boolean', string='COA Configured',
            store={
                'product.category': (lambda self, cr, uid, ids, c={}: ids, ['property_account_income_categ', 'property_account_expense_categ'], 50),
            }),
    }
    
    _defaults = {
        'is_coa_configured': _check_coa_configured,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
