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
from openerp.fields import Many2one



class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'

    _columns = {
        'valuation': fields.property(type='selection', selection=[('manual_periodic', 'Periodical (manual)'),
                                        ('real_time', 'Real Time (automated)')], string='Inventory Valuation',
                                        help="If real-time valuation is enabled for a product, the system will automatically write journal entries corresponding to stock moves, with product price as specified by the 'Costing Method'" \
                                             "The inventory variation account set on the product category will represent the current inventory value, and the stock input and stock output account will hold the counterpart moves for incoming and outgoing products."
                                        , required=True, copy=True),
        'cost_method': fields.property(type='selection', selection=[('standard', 'Standard Price'), ('average', 'Average Price'), ('real', 'Real Price')],
            help="""Standard Price: The cost price is manually updated at the end of a specific period (usually every year).
                    Average Price: The cost price is recomputed at each incoming shipment and used for the product valuation.
                    Real Price: The cost price displayed is the price of the last outgoing product (will be use in case of inventory loss for example).""",
            string="Costing Method", required=True, copy=True),
        'property_stock_account_input': fields.property(
            type='many2one',
            relation='account.account',
            string='Stock Input Account', 
            help="When doing real-time inventory valuation, counterpart journal items for all incoming stock moves will be posted in this account, unless "
                 "there is a specific valuation account set on the source location. When not set on the product, the one from the product category is used."),
        'property_stock_account_output': fields.property(
            type='many2one',
            relation='account.account',
            string='Stock Output Account', 
            help="When doing real-time inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account, unless "
                 "there is a specific valuation account set on the destination location. When not set on the product, the one from the product category is used."),
    }

    _defaults = {
        'valuation': 'manual_periodic',
    }


    def get_product_accounts(self, cr, uid, product_id, context=None):
        """ To get the stock input account, stock output account and stock journal related to product.
        @param product_id: product id
        @return: dictionary which contains information regarding stock input account, stock output account and stock journal
        """
        if context is None:
            context = {}
        product_obj = self.browse(cr, uid, product_id, context=context)

        stock_input_acc = product_obj.property_stock_account_input and product_obj.property_stock_account_input.id or False
        if not stock_input_acc:
            stock_input_acc = product_obj.categ_id.property_stock_account_input_categ and product_obj.categ_id.property_stock_account_input_categ.id or False

        stock_output_acc = product_obj.property_stock_account_output and product_obj.property_stock_account_output.id or False
        if not stock_output_acc:
            stock_output_acc = product_obj.categ_id.property_stock_account_output_categ and product_obj.categ_id.property_stock_account_output_categ.id or False

        journal_id = product_obj.categ_id.property_stock_journal and product_obj.categ_id.property_stock_journal.id or False
        account_valuation = product_obj.categ_id.property_stock_valuation_account_id and product_obj.categ_id.property_stock_valuation_account_id.id or False

        if not all([stock_input_acc, stock_output_acc, account_valuation, journal_id]):
            raise osv.except_osv(_('Error!'), _('''One of the following information is missing on the product or product category and prevents the accounting valuation entries to be created:
    Product: %s
    Stock Input Account: %s
    Stock Output Account: %s
    Stock Valuation Account: %s
    Stock Journal: %s
    ''') % (product_obj.name, stock_input_acc, stock_output_acc, account_valuation, journal_id))
        return {
            'stock_account_input': stock_input_acc,
            'stock_account_output': stock_output_acc,
            'stock_journal': journal_id,
            'property_stock_valuation_account_id': account_valuation
        }


    def do_change_standard_price(self, cr, uid, ids, new_price, context=None):
        """ Changes the Standard Price of Product and creates an account move accordingly."""
        location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        if context is None:
            context = {}
        user_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        loc_ids = location_obj.search(cr, uid, [('usage', '=', 'internal'), ('company_id', '=', user_company_id)])
        for rec_id in ids:
            datas = self.get_product_accounts(cr, uid, rec_id, context=context)
            for location in location_obj.browse(cr, uid, loc_ids, context=context):
                c = context.copy()
                c.update({'location': location.id, 'compute_child': False})
                product = self.browse(cr, uid, rec_id, context=c)

                diff = product.standard_price - new_price
                if not diff:
                    raise osv.except_osv(_('Error!'), _("No difference between standard price and new price!"))
                for prod_variant in product.product_variant_ids:
                    qty = prod_variant.qty_available
                    if qty:
                        # Accounting Entries
                        move_vals = {
                            'journal_id': datas['stock_journal'],
                            'company_id': location.company_id.id,
                        }
                        move_id = move_obj.create(cr, uid, move_vals, context=context)
    
                        if diff*qty > 0:
                            amount_diff = qty * diff
                            debit_account_id = datas['stock_account_input']
                            credit_account_id = datas['property_stock_valuation_account_id']
                        else:
                            amount_diff = qty * -diff
                            debit_account_id = datas['property_stock_valuation_account_id']
                            credit_account_id = datas['stock_account_output']
    
                        move_line_obj.create(cr, uid, {
                                        'name': _('Standard Price changed'),
                                        'account_id': debit_account_id,
                                        'debit': amount_diff,
                                        'credit': 0,
                                        'move_id': move_id,
                                        }, context=context)
                        move_line_obj.create(cr, uid, {
                                        'name': _('Standard Price changed'),
                                        'account_id': credit_account_id,
                                        'debit': 0,
                                        'credit': amount_diff,
                                        'move_id': move_id
                                        }, context=context)
            self.write(cr, uid, rec_id, {'standard_price': new_price})
        return True





class product_category(osv.osv):
    _inherit = 'product.category'
    _columns = {
        'property_stock_journal': fields.property(
            relation='account.journal',
            type='many2one',
            string='Stock Journal',
            help="When doing real-time inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed."),
        'property_stock_account_input_categ': fields.property(
            type='many2one',
            relation='account.account',
            string='Stock Input Account',
            help="When doing real-time inventory valuation, counterpart journal items for all incoming stock moves will be posted in this account, unless "
                 "there is a specific valuation account set on the source location. This is the default value for all products in this category. It "
                 "can also directly be set on each product"),
        'property_stock_account_output_categ': fields.property(
            type='many2one',
            relation='account.account',
            string='Stock Output Account',
            help="When doing real-time inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account, unless "
                 "there is a specific valuation account set on the destination location. This is the default value for all products in this category. It "
                 "can also directly be set on each product"),
        'property_stock_valuation_account_id': fields.property(
            type='many2one',
            relation='account.account',
            string="Stock Valuation Account",
            help="When real-time inventory valuation is enabled on a product, this account will hold the current value of the products.",),
    }

