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

from osv import fields, osv
from tools.translate import _

class product_category(osv.osv):
    _inherit = "product.category"
    _columns = {
        'property_account_creditor_price_difference_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Price Difference Account",
            method=True,
            view_load=True,
            help="This account will be used to value price difference between purchase price and cost price."),

        #Redefine fields to change help text for anglo saxon methodology.            
        'property_account_income_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Income Account",
            method=True,
            view_load=True,
            help="This account will be used to value outgoing stock for the current product category using sale price"),
        'property_account_expense_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Expense Account",
            method=True,
            view_load=True,
            help="This account will be used to value outgoing stock for the current product category using cost price"),                

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
            method=True,
            view_load=True,
            help="This account will be used to value price difference between purchase price and cost price."),
            
        #Redefine fields to change help text for anglo saxon methodology.
        'property_account_income': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Income Account",
            method=True,
            view_load=True,
            help="This account will be used to value outgoing stock for the current product category using sale price"),
        'property_account_expense': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Expense Account",
            method=True,
            view_load=True,
            help="This account will be used to value outgoing stock for the current product category using cost price"),                

    }
product_template()

class product_product(osv.osv):
    _inherit = "product.product"

    def do_change_standard_price(self, cr, uid, ids, datas, context=None):
        """ Changes the Standard Price of Product and creates an account move accordingly.
        @param datas : dict. contain default datas like new_price, stock_output_account, stock_input_account, stock_journal
        @param context: A standard dictionary
        @return:

        """
        product_obj=self.browse(cr, uid, ids, context=context)[0]
        stock_price_diff_account = product_obj.property_account_creditor_price_difference and product_obj.property_account_creditor_price_difference.id or False

        if not stock_price_diff_account:
            stock_price_diff_account = product_obj.categ_id.property_account_creditor_price_difference_categ and product_obj.categ_id.property_account_creditor_price_difference_categ.id or False
        if not stock_price_diff_account:
            raise osv.except_osv(_('Error!'),_('There is no price difference account defined ' \
                                               'for this product: "%s" (id: %d)') % (product_obj.name, product_obj.id,))
        datas['stock_input_account'] = stock_price_diff_account
        datas['stock_output_account'] = stock_price_diff_account

        return super(product_product, self).do_change_standard_price(cr, uid, ids, datas, context)

product_product()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

