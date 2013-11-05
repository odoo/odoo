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

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Stock Location
#----------------------------------------------------------

class stock_location(osv.osv):
    _inherit = "stock.location"

    _columns = {
        'valuation_in_account_id': fields.many2one('account.account', 'Stock Valuation Account (Incoming)', domain=[('type', '=', 'other')],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved from an internal location "
                                                        "into this location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),
        'valuation_out_account_id': fields.many2one('account.account', 'Stock Valuation Account (Outgoing)', domain=[('type', '=', 'other')],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved out of this location "
                                                        "and into an internal location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),
    }

#----------------------------------------------------------
# Quants
#----------------------------------------------------------

class stock_quant(osv.osv):
    _inherit = "stock.quant"

    def _get_inventory_value(self, cr, uid, line, prodbrow, context=None):
        #TODO: what in case of partner_id
        if prodbrow[(line.company_id.id, line.product_id.id)].cost_method in ('real'):
            return line.cost * line.qty
        return super(stock_quant, self)._get_inventory_value(cr, uid, line, prodbrow, context=context)

    def _price_update(self, cr, uid, quant_ids, newprice, context=None):
        ''' This function is called at the end of negative quant reconciliation and does the accounting entries adjustemnts and the update of the product cost price if needed
        '''
        if context is None:
            context = {}
        super(stock_quant, self)._price_update(cr, uid, quant_ids, newprice, context=context)
        ctx = context.copy()
        for quant in self.browse(cr, uid, quant_ids, context=context):
            move = self._get_latest_move(cr, uid, quant, context=context)
            # this is where we post accounting entries for adjustment
            ctx['force_valuation_amount'] = newprice - quant.cost
            self._account_entry_move(cr, uid, quant, move, context=ctx)
            #update the standard price of the product, only if we would have done it if we'd have had enough stock at first, which means
            #1) the product cost's method is 'real'
            #2) we just fixed a negative quant caused by an outgoing shipment
            if quant.product_id.cost_method == 'real' and quant.location_id.usage != 'internal':
                self.pool.get('stock.move')._store_average_cost_price(cr, uid, move, context=context)

    """
    Accounting Valuation Entries

    location_from: can be None if it's a new quant
    """
    def _account_entry_move(self, cr, uid, quant, move, context=None):
        location_from = move.location_id
        location_to = move.location_dest_id
        if context is None:
            context = {}
        if quant.product_id.valuation != 'real_time':
            return False
        if quant.owner_id:
            #if the quant isn't owned by the company, we don't make any valuation entry
            return False
        if quant.qty <= 0:
            #we don't make any stock valuation for negative quants because the valuation is already made for the counterpart.
            #At that time the valuation will be made at the product cost price and afterward there will be new accounting entries
            #to make the adjustments when we know the real cost price.
            return False
        company_from = self._location_owner(cr, uid, quant, location_from, context=context)
        company_to = self._location_owner(cr, uid, quant, location_to, context=context)
        if company_from == company_to:
            return False

        # Create Journal Entry for products arriving in the company
        if company_to:
            ctx = context.copy()
            ctx['force_company'] = company_to.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            if location_from and location_from.usage == 'customer':
                #goods returned from customer
                self._create_account_move_line(cr, uid, quant, move, acc_dest, acc_valuation, journal_id, context=ctx)
            else:
                self._create_account_move_line(cr, uid, quant, move, acc_src, acc_valuation, journal_id, context=ctx)

        # Create Journal Entry for products leaving the company
        if company_from:
            ctx = context.copy()
            ctx['force_company'] = company_from.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            if location_to and location_to.usage == 'supplier':
                #goods returned to supplier
                self._create_account_move_line(cr, uid, quant, move, acc_valuation, acc_src, journal_id, context=ctx)
            else:
                self._create_account_move_line(cr, uid, quant, move, acc_valuation, acc_dest, journal_id, context=ctx)


    def move_single_quant(self, cr, uid, quant, qty, move, lot_id=False, owner_id=False, package_id= False, context=None):
        quant_record = super(stock_quant, self).move_single_quant(cr, uid, quant, qty, move, lot_id = lot_id, owner_id = owner_id, package_id = package_id, context=context)
        self._account_entry_move(cr, uid, quant_record, move, context=context)
        return quant_record


    def _get_accounting_data_for_valuation(self, cr, uid, move, context=None):
        """
        Return the accounts and journal to use to post Journal Entries for the real-time
        valuation of the quant.

        :param context: context dictionary that can explicitly mention the company to consider via the 'force_company' key
        :returns: journal_id, source account, destination account, valuation account
        :raise: osv.except_osv() is any mandatory account or journal is not defined.
        """
        product_obj = self.pool.get('product.product')
        accounts = product_obj.get_product_accounts(cr, uid, move.product_id.id, context)
        if move.location_id.valuation_out_account_id:
            acc_src = move.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts['stock_account_input']

        if move.location_dest_id.valuation_in_account_id:
            acc_dest = move.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts['stock_account_output']

        acc_valuation = accounts.get('property_stock_valuation_account_id', False)
        journal_id = accounts['stock_journal']

        if not all([acc_src, acc_dest, acc_valuation, journal_id]):
            raise osv.except_osv(_('Error!'), _('''One of the following information is missing on the product or product category and prevents the accounting valuation entries to be created:
    Stock Input Account: %s
    Stock Output Account: %s
    Stock Valuation Account: %s
    Stock Journal: %s
    ''') % (acc_src, acc_dest, acc_valuation, journal_id))
        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_line(self, cr, uid, quant, move, credit_account_id, debit_account_id, context=None):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        if context.get('force_valuation_amount'):
            valuation_amount = context.get('force_valuation_amount')
        else:
            valuation_amount = quant.product_id.cost_method == 'real' and quant.cost or quant.product_id.standard_price
        #the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        #the company currency... so we need to use round() before creating the accounting entries.
        valuation_amount = currency_obj.round(cr, uid, quant.company_id.currency_id, valuation_amount * quant.qty)
        partner_id = (move.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(move.picking_id.partner_id).id) or False
        debit_line_vals = {
                    'name': move.name,
                    'product_id': quant.product_id.id,
                    'quantity': quant.qty,
                    'product_uom_id': quant.product_id.uom_id.id,
                    'ref': move.picking_id and move.picking_id.name or False,
                    'date': time.strftime('%Y-%m-%d'),
                    'partner_id': partner_id,
                    'debit': valuation_amount > 0 and valuation_amount or 0,
                    'credit': valuation_amount < 0 and -valuation_amount or 0,
                    'account_id': debit_account_id,
        }
        credit_line_vals = {
                    'name': move.name,
                    'product_id': quant.product_id.id,
                    'quantity': quant.qty,
                    'product_uom_id': quant.product_id.uom_id.id,
                    'ref': move.picking_id and move.picking_id.name or False,
                    'date': time.strftime('%Y-%m-%d'),
                    'partner_id': partner_id,
                    'credit': valuation_amount > 0 and valuation_amount or 0,
                    'debit': valuation_amount < 0 and -valuation_amount or 0,
                    'account_id': credit_account_id,
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]

    def _create_account_move_line(self, cr, uid, quant, move, credit_account_id, debit_account_id, journal_id, context=None):
        move_obj = self.pool.get('account.move')
        move_lines = self._prepare_account_move_line(cr, uid, quant, move, credit_account_id, debit_account_id, context=context)
        return move_obj.create(cr, uid, {'journal_id': journal_id,
                                  'line_id': move_lines,
                                  'ref': move.picking_id and move.picking_id.name}, context=context)

    #def _reconcile_single_negative_quant(self, cr, uid, to_solve_quant, quant, quant_neg, qty, context=None):
    #    move = self._get_latest_move(cr, uid, to_solve_quant, context=context)
    #    quant_neg_position = quant_neg.negative_dest_location_id.usage
    #    remaining_solving_quant, remaining_to_solve_quant = super(stock_quant, self)._reconcile_single_negative_quant(cr, uid, to_solve_quant, quant, quant_neg, qty, context=context)
    #    #update the standard price of the product, only if we would have done it if we'd have had enough stock at first, which means
    #    #1) there isn't any negative quant anymore
    #    #2) the product cost's method is 'real'
    #    #3) we just fixed a negative quant caused by an outgoing shipment
    #    if not remaining_to_solve_quant and move.product_id.cost_method == 'real' and quant_neg_position != 'internal':
    #        self.pool.get('stock.move')._store_average_cost_price(cr, uid, move, context=context)
    #    return remaining_solving_quant, remaining_to_solve_quant

class stock_move(osv.osv):
    _inherit = "stock.move"

    def action_done(self, cr, uid, ids, negatives = False, context=None):
        self.product_price_update_before_done(cr, uid, ids, context=context)
        super(stock_move, self).action_done(cr, uid, ids, negatives=negatives, context=context)
        self.product_price_update_after_done(cr, uid, ids, context=context)

    def _store_average_cost_price(self, cr, uid, move, context=None):
        ''' move is a browe record '''
        product_obj = self.pool.get('product.product')
        move.refresh()
        if any([q.qty <= 0 for q in move.quant_ids]):
            #if there is a negative quant, the standard price shouldn't be updated
            return
        #Note: here we can't store a quant.cost directly as we may have moved out 2 units (1 unit to 5€ and 1 unit to 7€) and in case of a product return of 1 unit, we can't know which of the 2 costs has to be used (5€ or 7€?). So at that time, thanks to the average valuation price we are storing we will svaluate it at 6€
        average_valuation_price = 0.0
        for q in move.quant_ids:
            average_valuation_price += q.qty * q.cost
        average_valuation_price = average_valuation_price / move.product_qty
        # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
        product_obj.write(cr, SUPERUSER_ID, move.product_id.id, {'standard_price': average_valuation_price}, context=context)
        self.write(cr, uid, move.id, {'price_unit': average_valuation_price}, context=context)

    def product_price_update_before_done(self, cr, uid, ids, context=None):
        product_obj = self.pool.get('product.product')
        for move in self.browse(cr, uid, ids, context=context):
            #adapt standard price on incomming moves if the product cost_method is 'average'
            if (move.location_id.usage == 'supplier') and (move.product_id.cost_method == 'average'):
                product = move.product_id
                company_currency_id = move.company_id.currency_id.id
                ctx = {'currency_id': company_currency_id}
                product_avail = product.qty_available
                if product.qty_available <= 0:
                    new_std_price = move.price_unit
                else:
                    # Get the standard price
                    amount_unit = product.standard_price
                    new_std_price = ((amount_unit * product_avail) + (move.price_unit * move.product_qty)) / (product_avail + move.product_qty)
                # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
                product_obj.write(cr, SUPERUSER_ID, [product.id], {'standard_price': new_std_price}, context=context)

    def product_price_update_after_done(self, cr, uid, ids, context=None):
        '''
        This method adapts the price on the product when necessary
        '''
        for move in self.browse(cr, uid, ids, context=context):
            #adapt standard price on outgoing moves if the product cost_method is 'real', so that a return
            #or an inventory loss is made using the last value used for an outgoing valuation.
            if move.product_id.cost_method == 'real' and move.location_dest_id.usage != 'internal':
                #store the average price of the move on the move and product form
                self._store_average_cost_price(cr, uid, move, context=context)
