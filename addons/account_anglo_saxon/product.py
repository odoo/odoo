##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class product_category(osv.osv):
    _inherit = "product.category"
    _columns = {
        'property_account_creditor_price_difference_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Price Difference Account",
            view_load=True,
            help="This account will be used to value price difference between purchase price and cost price."),

        #Redefine fields to change help text for anglo saxon methodology.            
        'property_account_income_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Income Account",
            view_load=True,
            help="This account will be used to value outgoing stock using sale price."),
        'property_account_expense_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Expense Account",
            view_load=True,
            help="This account will be used to value outgoing stock using cost price."),

    }
product_category()

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'property_account_creditor_price_difference': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Price Difference Account",
            view_load=True,
            help="This account will be used to value price difference between purchase price and cost price."),
            
        #Redefine fields to change help text for anglo saxon methodology.
        'property_account_income': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Income Account",
            view_load=True,
            help="This account will be used to value outgoing stock using sale price."),
        'property_account_expense': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Expense Account",
            view_load=True,
            help="This account will be used to value outgoing stock using cost price."),

    }
product_template()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

