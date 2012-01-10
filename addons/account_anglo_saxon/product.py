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
        location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        if context is None:
            context = {}

        new_price = datas.get('new_price', 0.0)
        journal_id = datas.get('stock_journal', False)
        product_obj=self.browse(cr, uid, ids, context=context)[0]
        account_variation = product_obj.categ_id.property_stock_variation
        account_variation_id = account_variation and account_variation.id or False
        stock_price_diff_account = datas.get('stock_price_diff_account',False)
        
        if not account_variation_id: raise osv.except_osv(_('Error!'), _('Variation Account is not specified for Product Category: %s') % (product_obj.categ_id.name))
        if not stock_price_diff_account:
            stock_price_diff_account = product_obj.categ_id.property_account_creditor_price_difference_categ and product_obj.categ_id.property_account_creditor_price_difference_categ.id or False
        if not stock_price_diff_account:
            raise osv.except_osv(_('Error!'),_('There is no price diffrent account defined ' \
                                               'for this product: "%s" (id: %d)') % (product_obj.name, product_obj.id,))
        move_ids = []
        loc_ids = location_obj.search(cr, uid,[('usage','=','internal')])
        for rec_id in ids:
            for location in location_obj.browse(cr, uid, loc_ids, context=context):
                c = context.copy()
                c.update({
                    'location': location.id,
                    'compute_child': False
                })

                product = self.browse(cr, uid, rec_id, context=c)
                qty = product.qty_available
                diff = product.standard_price - new_price
                if not diff: raise osv.except_osv(_('Error!'), _("Could not find any difference between standard price and new price!"))
                if qty:
                    company_id = location.company_id and location.company_id.id or False
                    if not company_id: raise osv.except_osv(_('Error!'), _('Company is not specified in Location'))
                    #
                    # Accounting Entries
                    #
                    if not journal_id:
                        journal_id = product.categ_id.property_stock_journal and product.categ_id.property_stock_journal.id or False
                    if not journal_id:
                        raise osv.except_osv(_('Error!'),
                            _('There is no journal defined '\
                                'on the product category: "%s" (id: %d)') % \
                                (product.categ_id.name,
                                    product.categ_id.id,))
                    move_id = move_obj.create(cr, uid, {
                                'journal_id': journal_id,
                                'company_id': company_id
                                })

                    move_ids.append(move_id)


                    if diff > 0:
                        amount_diff = qty * diff
                        move_line_obj.create(cr, uid, {
                                    'name': product.name,
                                    'account_id': stock_price_diff_account,
                                    'debit': amount_diff,
                                    'move_id': move_id,
                                    })
                        move_line_obj.create(cr, uid, {
                                    'name': product.categ_id.name,
                                    'account_id': account_variation_id,
                                    'credit': amount_diff,
                                    'move_id': move_id
                                    })
                    elif diff < 0:
                        amount_diff = qty * -diff
                        move_line_obj.create(cr, uid, {
                                        'name': product.name,
                                        'account_id': stock_price_diff_account,
                                        'credit': amount_diff,
                                        'move_id': move_id
                                    })
                        move_line_obj.create(cr, uid, {
                                        'name': product.categ_id.name,
                                        'account_id': account_variation_id,
                                        'debit': amount_diff,
                                        'move_id': move_id
                                    })

            self.write(cr, uid, rec_id, {'standard_price': new_price})

        return move_ids
    
product_product()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

