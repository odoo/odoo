# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.cr_uid_records_context
    def _get_inventory_value(self, cr, uid, quant, context):
        if quant.product_id.cost_method in ('real',):
            return quant.cost * quant.qty
        return super(StockQuant, self)._get_inventory_value(cr, uid, quant, context)

    @api.multi
    def _price_update(self, newprice):
        ''' This function is called at the end of negative quant reconciliation and does the accounting entries adjustemnts and the update of the product cost price if needed
        '''
        super(StockQuant, self)._price_update(newprice)
        AccountMove = self.env['account.move']
        for quant in self:
            move = self._get_latest_move(quant)
            valuation_update = newprice - quant.cost
            # this is where we post accounting entries for adjustment, if needed
            # If neg quant period already closed (likely with manual valuation), skip update
            if not quant.company_id.currency_id.is_zero(valuation_update) and AccountMove.browse(move.id)._check_lock_date():
                quant.with_context(force_valuation_amount=valuation_update)._account_entry_move(move)

            #update the standard price of the product, only if we would have done it if we'd have had enough stock at first, which means
            #1) the product cost's method is 'real'
            #2) we just fixed a negative quant caused by an outgoing shipment
            if quant.product_id.cost_method == 'real' and quant.location_id.usage != 'internal':
                move._store_average_cost_price()

    def _account_entry_move(self, move):
        """
        Accounting Valuation Entries

        move: Move to use. browse record
        """
        StockLocation = self.env['stock.location']
        location_from = move.location_id
        location_to = self[0].location_id
        company_from = StockLocation._location_owner(location_from)
        company_to = StockLocation._location_owner(location_to)

        if move.product_id.valuation != 'real_time':
            return False
        if move.product_id.type != 'product':
            #No stock valuation for consumable products
            return False
        for quant in self:
            if quant.owner_id:
                #if the quant isn't owned by the company, we don't make any valuation entry
                return False
            if quant.qty <= 0:
                #we don't make any stock valuation for negative quants because the valuation is already made for the counterpart.
                #At that time the valuation will be made at the product cost price and afterward there will be new accounting entries
                #to make the adjustments when we know the real cost price.
                return False

        #in case of routes making the link between several warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        # Create Journal Entry for products arriving in the company
        if company_to and (move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage == 'internal' or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = self.with_context(force_company=company_to.id)._get_accounting_data_for_valuation(move)
            if location_from and location_from.usage == 'customer':
                #goods returned from customer
                self.with_context(force_company=company_to.id)._create_account_move_line(move, acc_dest, acc_valuation, journal_id)
            else:
                self.with_context(force_company=company_to.id)._create_account_move_line(move, acc_src, acc_valuation, journal_id)

        # Create Journal Entry for products leaving the company
        if company_from and (move.location_id.usage == 'internal' and move.location_dest_id.usage not in ('internal', 'transit') or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = self.with_context(force_company=company_from.id)._get_accounting_data_for_valuation(move)
            if location_to and location_to.usage == 'supplier':
                #goods returned to supplier
                self.with_context(force_company=company_from.id)._create_account_move_line(move, acc_valuation, acc_src, journal_id)
            else:
                self.with_context(force_company=company_from.id)._create_account_move_line(move, acc_valuation, acc_dest, journal_id)

    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, force_location_from=False, force_location_to=False):
        quant = super(StockQuant, self)._quant_create(qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=force_location_from, force_location_to=force_location_to)
        quant._account_entry_move(move)
        return quant

    @api.model
    def move_quants_write(self, quants, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        res = super(StockQuant, self).move_quants_write(quants, move, location_dest_id,  dest_package_id, lot_id=lot_id, entire_pack=entire_pack)
        quants = reduce(lambda x, y: x + y, quants)
        quants._account_entry_move(move)
        return res

    def _get_accounting_data_for_valuation(self, move):
        """
        Return the accounts and journal to use to post Journal Entries for the real-time
        valuation of the quant.

        :returns: journal_id, source account, destination account, valuation account
        """
        accounts = move.product_id.product_tmpl_id.get_product_accounts()
        if move.location_id.valuation_out_account_id:
            acc_src = move.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts['stock_input'].id

        if move.location_dest_id.valuation_in_account_id:
            acc_dest = move.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts['stock_output'].id

        acc_valuation = accounts.get('stock_valuation') and accounts['stock_valuation'].id
        if not accounts.get('stock_journal'):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (move.product_id.name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (move.product_id.name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_line(self, move, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        valuation_amount = self.env.context.get('force_valuation_amount')
        if not valuation_amount:
            if move.product_id.cost_method == 'average':
                valuation_amount = cost if move.location_id.usage == 'supplier' and move.location_dest_id.usage == 'internal' else move.product_id.standard_price
            else:
                valuation_amount = cost if move.product_id.cost_method == 'real' else move.product_id.standard_price
        #the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        #the company currency... so we need to use round() before creating the accounting entries.
        debit_value = move.company_id.currency_id.round(valuation_amount * qty)
        #check that all data is correct
        if move.company_id.currency_id.is_zero(debit_value):
            raise UserError(_("The found valuation amount for product %s is zero. Which means there is probably a configuration error. Check the costing method and the standard price") % (move.product_id.name,))
        credit_value = debit_value

        if move.product_id.cost_method == 'average' and move.company_id.anglo_saxon_accounting:
            #in case of a supplier return in anglo saxon mode, for products in average costing method, the stock_input
            #account books the real purchase price, while the stock account books the average price. The difference is
            #booked in the dedicated price difference account.
            if move.location_dest_id.usage == 'supplier' and move.origin_returned_move_id and move.origin_returned_move_id.purchase_line_id:
                debit_value = move.origin_returned_move_id.price_unit * qty
            #in case of a customer return in anglo saxon mode, for products in average costing method, the stock valuation
            #is made using the original average price to negate the delivery effect.
            if move.location_id.usage == 'customer' and move.origin_returned_move_id:
                debit_value = move.origin_returned_move_id.price_unit * qty
                credit_value = debit_value
        partner_id = (move.picking_id.partner_id and self.env['res.partner']._find_accounting_partner(move.picking_id.partner_id).id) or False
        debit_line_vals = {
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'quantity': qty,
                    'product_uom_id': move.product_id.uom_id.id,
                    'ref': move.picking_id.name,
                    'partner_id': partner_id,
                    'debit': debit_value,
                    'credit': 0,
                    'account_id': debit_account_id,
        }
        credit_line_vals = {
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'quantity': qty,
                    'product_uom_id': move.product_id.uom_id.id,
                    'ref': move.picking_id.name,
                    'partner_id': partner_id,
                    'credit': credit_value,
                    'debit': 0,
                    'account_id': credit_account_id,
        }
        res = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        if credit_value != debit_value:
            #for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = move.product_id.property_account_creditor_price_difference or move.product_id.categ_id.property_account_creditor_price_difference_categ
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))
            price_diff_line = {
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'quantity': qty,
                    'product_uom_id': move.product_id.uom_id.id,
                    'ref': move.picking_id and move.picking_id.name,
                    'partner_id': partner_id,
                    'credit': diff_amount > 0 and diff_amount or 0,
                    'debit': diff_amount < 0 and -diff_amount or 0,
                    'account_id': price_diff_account.id,
            }
            res.append((0, 0, price_diff_line))
        return res

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
        AccountMove = self.env['account.move']
        #group quants by cost
        quant_cost_qty = {}
        for quant in self:
            quant_cost_qty.setdefault(quant.cost, 0)
            quant_cost_qty[quant.cost] += quant.qty
        for cost, qty in quant_cost_qty.items():
            move_lines = self._prepare_account_move_line(move, qty, cost, credit_account_id, debit_account_id)
            date = self.env.context.get('force_period_date', move.date)
            account_move = AccountMove.create({'journal_id': journal_id,
                                          'line_ids': move_lines,
                                          'date': date,
                                          'ref': move.picking_id.name})
            account_move.post()
