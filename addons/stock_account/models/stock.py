# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, pycompat

import logging
_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    accounting_date = fields.Date(
        'Force Accounting Date',
        help="Choose the accounting date at which you want to value the stock "
             "moves created by the inventory instead of the default one (the "
             "inventory end date)")

    @api.multi
    def post_inventory(self):
        acc_inventories = self.filtered(lambda inventory: inventory.accounting_date)
        for inventory in acc_inventories:
            res = super(StockInventory, inventory.with_context(force_period_date=inventory.accounting_date)).post_inventory()
        other_inventories = self - acc_inventories
        if other_inventories:
            res = super(StockInventory, other_inventories).post_inventory()
        return res


class StockLocation(models.Model):
    _inherit = "stock.location"

    valuation_in_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Incoming)',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved from an internal location "
             "into this location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")
    valuation_out_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Outgoing)',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved out of this location "
             "and into an internal location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.multi
    def write(self, vals):
        super(StockMoveLine, self).write(vals)
        if 'qty_done' in vals:
            for move in self.mapped('move_id').filtered(lambda m: m.state == 'done'):
                move.value = move.quantity_done * move.price_unit
                move.replay()
    @api.multi
    def _price_update(self, newprice):
        ''' This function is called at the end of negative quant reconciliation
        and does the accounting entries adjustemnts and the update of the product
        cost price if needed '''
        super(StockQuant, self)._price_update(newprice)
        for quant in self:
            move = quant._get_latest_move()
            valuation_update = newprice - quant.cost
            # this is where we post accounting entries for adjustment, if needed
            # If neg quant period already closed (likely with manual valuation), skip update
            if not quant.company_id.currency_id.is_zero(valuation_update) and move._check_lock_date():
                quant.with_context(force_valuation_amount=valuation_update)._account_entry_move(move)

            # update the standard price of the product, only if we would have
            # done it if we'd have had enough stock at first, which means
            # 1) the product cost's method is 'real'
            # 2) we just fixed a negative quant caused by an outgoing shipment
            if quant.product_id.cost_method == 'real' and quant.location_id.usage != 'internal':
                move._store_average_cost_price()

    def _account_entry_move(self, move):
        """ Accounting Valuation Entries """
        #TODO OCO move est un stock.move ! C'est donc bien pratique !

        if move.product_id.type != 'product' or move.product_id.valuation != 'real_time':
            # no stock valuation for consumable products
            return False
        if any(quant.owner_id or quant.qty <= 0 for quant in self):
            # if the quant isn't owned by the company, we don't make any valuation en
            # we don't make any stock valuation for negative quants because the valuation is already made for the counterpart.
            # At that time the valuation will be made at the product cost price and afterward there will be new accounting entries
            # to make the adjustments when we know the real cost price.
            return False

        location_from = move.location_id
        location_to = self[0].location_id  # TDE FIXME: as the accounting is based on this value, should probably check all location_to to be the same
        company_from = location_from.usage == 'internal' and location_from.company_id or False
        company_to = location_to and (location_to.usage == 'internal') and location_to.company_id or False

        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if company_to and (move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage == 'internal' or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            if location_from and location_from.usage == 'customer':  # goods returned from customer
                self.with_context(force_company=company_to.id)._create_account_move_line(move, acc_dest, acc_valuation, journal_id)
            else:
                self.with_context(force_company=company_to.id)._create_account_move_line(move, acc_src, acc_valuation, journal_id)

        # Create Journal Entry for products leaving the company
        if company_from and (move.location_id.usage == 'internal' and move.location_dest_id.usage not in ('internal', 'transit') or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                self.with_context(force_company=company_from.id)._create_account_move_line(move, acc_valuation, acc_src, journal_id)
            else:
                self.with_context(force_company=company_from.id)._create_account_move_line(move, acc_valuation, acc_dest, journal_id)

        if move.company_id.anglo_saxon_accounting and move.location_id.usage == 'supplier' and move.location_dest_id.usage == 'customer':
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            self.with_context(force_company=move.company_id.id)._create_account_move_line(move, acc_src, acc_dest, journal_id)

        if move.company_id.anglo_saxon_accounting: #TODO OCO : voir si ça fonctionne comme tu le veux
            move.reconcile_valuation_with_invoices()

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
        # group quants by cost
        quant_cost_qty = defaultdict(lambda: 0.0)
        for quant in self:
            quant_cost_qty[quant.cost] += quant.qty

        AccountMove = self.env['account.move']
        for cost, qty in pycompat.items(quant_cost_qty):
            move_lines = move._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
            if move_lines:
                date = self._context.get('force_period_date', fields.Date.context_today(self))
                new_account_move = AccountMove.create({
                    'journal_id': journal_id,
                    'line_ids': move_lines,
                    'date': date,
                    'ref': move.picking_id.name})
                new_account_move.post()
                new_account_move.message_post_with_view('mail.message_origin_link',
                        values={'self': new_account_move, 'origin': move.picking_id},
                        subtype_id=self.env.ref('mail.mt_note').id)
                move.write({'stock_account_valuation_account_move_ids': [(4, new_account_move.id, None)]})


    def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, force_location_from=False, force_location_to=False):
        quant = super(StockQuant, self)._quant_create_from_move(qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=force_location_from, force_location_to=force_location_to)
        quant._account_entry_move(move)
        if move.product_id.valuation == 'real_time':
            # If the precision required for the variable quant cost is larger than the accounting
            # precision, inconsistencies between the stock valuation and the accounting entries
            # may arise.
            # For example, a box of 13 units is bought 15.00. If the products leave the
            # stock one unit at a time, the amount related to the cost will correspond to
            # round(15/13, 2)*13 = 14.95. To avoid this case, we split the quant in 12 + 1, then
            # record the difference on the new quant.
            # We need to make sure to able to extract at least one unit of the product. There is
            # an arbitrary minimum quantity set to 2.0 from which we consider we can extract a
            # unit and adapt the cost.
            curr_rounding = move.company_id.currency_id.rounding
            cost_rounded = float_round(quant.cost, precision_rounding=curr_rounding)
            cost_correct = cost_rounded
            if float_compare(quant.product_id.uom_id.rounding, 1.0, precision_digits=1) == 0\
                    and float_compare(quant.qty * quant.cost, quant.qty * cost_rounded, precision_rounding=curr_rounding) != 0\
                    and float_compare(quant.qty, 2.0, precision_rounding=quant.product_id.uom_id.rounding) >= 0:
                quant_correct = quant._quant_split(quant.qty - 1.0)
                cost_correct += (quant.qty * quant.cost) - (quant.qty * cost_rounded)
                quant.sudo().write({'cost': cost_rounded})
                quant_correct.sudo().write({'cost': cost_correct})
        return quant

    def _quant_update_from_move(self, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        res = super(StockQuant, self)._quant_update_from_move(move, location_dest_id, dest_package_id, lot_id=lot_id, entire_pack=entire_pack)
        self._account_entry_move(move)
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)",
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')

    value = fields.Float()
    cumulated_value = fields.Float()
    remaining_qty = fields.Float()
    last_done_move_id = fields.Many2one('stock.move')
    last_done_remaining_qty = fields.Float()
    last_done_qty = fields.Float()

    # TODO: add constraints remaining_qty > 0
    # TODO: add constrain price_unit = 0 on done move?
    stock_account_valuation_account_move_ids = fields.Many2many(comodel_name='account.move', string='Accounting entries', help="Accounting entries used for perpetual valuation of this move.")

    def _set_default_price_moves(self):
        # When the cost method is in real or average price, the price can be set to 0.0 on the PO
        # So the price doesn't have to be updated
        moves = super(StockMove, self)._set_default_price_moves()
        return moves.filtered(lambda m: m.product_id.cost_method not in ('real', 'average'))

    @api.multi
    def _get_price_unit(self):
        self.ensure_one()
        if self.product_id.cost_method == 'average':
            return self.product_id.average_price or self.product_id.standard_price
        if self.product_id.cost_method == 'fifo':
            move = self.search([('product_id', '=', self.product_id.id),
                         ('state', '=', 'done'),
                         ('location_id.usage', '=', 'internal'),
                         ('location_dest_id.usage', '!=', 'internal')], order='date desc', limit=1)
            if move:
                return move.price_unit or self.product_id.standard_price
        return self.product_id.standard_price

    def _update_future_cumulated_value(self, value):
        self.ensure_one()
        moves = self.search([('state', '=', 'done'),
                     ('date', '>',  self.date),
                     ('product_id', '=', self.product_id.id)])
        for move in moves:
            move.value += value

#     def change_move_value_in_the_past(self, value):
#         self.ensure_one()
#         if self.product_id.cost_method == 'fifo':
#             moves = self.search([('state', '=', 'done'),
#                          ('date', '>',  self.date),
#                          ('product_id', '=', self.product_id.id)])
#             if self.location_id.usage not in ('internal', 'transit'):
#                 if move.last_done_move_id and move.last_done_remaining_qty:

    @api.multi
    def replay(self):
        # Easy scenario: avergae /done
        # search last move before this one
        start_move = self.search([('product_id', '=', self.product_id.id),
                     ('state', '=', 'done'),
                     ('date', '<', self.date)], limit=1, order='date desc') #filter on outgoing/incoming moves
        next_moves = self.search([('product_id', '=', self.product_id.id),
                     ('state', '=', 'done'),
                     ('date', '>', start_move.date)], order='date') # filter on outgoing/incoming moves
        if start_move:
            last_cumulated_value = start_move.cumulated_value
            last_done_qty_available = start_move.last_done_qty
        else:
            last_cumulated_value = 0.0
            last_done_qty_available = 0.0
        if self.product_id.cost_method == 'average':
            for move in next_moves:
                if move.location_id.usage in ('internal', 'transit') and move.location_dest_id.usage not in ('internal', 'transit'):
                    if last_done_qty_available:
                        move.value = - ((last_cumulated_value / last_done_qty_available) * move.product_qty)
                    last_done_qty_available -= move.product_qty
                else:
                    last_done_qty_available += move.product_qty
                move.cumulated_value = last_cumulated_value + move.value
                last_cumulated_value = move.cumulated_value
                move.last_done_qty = last_done_qty_available


        # FIFO: needs dict with qty_remaining to replay algorithm


        # update cumulated_value according to value

        # update outs according to values

        # update


    @api.multi
    def action_done(self):
        qty_available = {}
        for move in self:
            #Should write move.price_unit here maybe, certainly on incoming
            if move.product_id.cost_method == 'average':
                qty_available[move.product_id.id] = move.product_id.qty_available
        res = super(StockMove, self).action_done()
        for move in res:
            if move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage in ('internal', 'transit'):
                if move.product_id.cost_method in ['fifo', 'average']:
                    if not move.price_unit:
                        move.price_unit = move._get_price_unit()
                    move.value = move.price_unit * move.product_qty
                    move.cumulated_value = move.product_id._get_latest_cumulated_value(not_move=move) + move.value
                    move.remaining_qty = move.product_qty
                    if move.product_id.cost_method == 'fifo':
                        # If you find an out with qty_remaining (because of negative stock), you can change it over there
                        candidates_out = move.product_id._get_candidates_out_move()
                        qty_to_take = move.product_qty
                        for candidate in candidates_out:
                            if candidate.remaining_qty < qty_to_take:
                                qty_taken_on_candidate = candidate.remaining_qty
                            else:
                                qty_taken_on_candidate = qty_to_take
                            candidate.remaining_qty -= qty_taken_on_candidate
                            move.remaining_qty -= qty_taken_on_candidate
                            qty_to_take -= qty_taken_on_candidate
                            candidate.value += move.price_unit * qty_taken_on_candidate
                            candidate.cumulated_value += move.price_unit * qty_taken_on_candidate
                            candidate._update_future_cumulated_value(move.price_unit * qty_taken_on_candidate)
                            candidate.price_unit = candidate.value / candidate.product_qty
                    move.last_done_qty = move.product_id.qty_available
                else:
                    move.price_unit = move.product_id.standard_price
                    move.value = move.price_unit * move.product_qty
            elif move.location_id.usage in ('internal', 'transit') and move.location_dest_id.usage not in ('internal', 'transit'):
                if move.product_id.cost_method == 'fifo':
                    qty_to_take = move.product_qty
                    tmp_value = 0
                    candidates = move.product_id._get_candidates_move()
                    last_candidate = False
                    for candidate in candidates:
                        if candidate.remaining_qty <= qty_to_take:
                            qty_taken_on_candidate = candidate.remaining_qty
                        else:
                            qty_taken_on_candidate = qty_to_take
                        tmp_value += qty_taken_on_candidate * candidate.price_unit
                        candidate.remaining_qty -= qty_taken_on_candidate
                        qty_to_take -= qty_taken_on_candidate
                        if qty_to_take == 0:
                            break
                        last_candidate = candidate
                    if last_candidate:
                        move.last_done_move_id = last_candidate.id
                        move.last_done_remaining_qty = last_candidate.remaining_qty
                    if qty_to_take > 0:
                        move.remaining_qty = qty_to_take # In case there are no candidates to match, put standard price on it
                    move.value = -tmp_value
                    move.cumulated_value = move.product_id._get_latest_cumulated_value(not_move=move) + move.value
                    move.last_done_qty = move.product_id.qty_available
                elif move.product_id.cost_method == 'average':
                    curr_rounding = move.company_id.currency_id.rounding
                    avg_price_unit = float_round(move.product_id._get_latest_cumulated_value(not_move=move) / qty_available[move.product_id.id], precision_rounding=curr_rounding)
                    move.value = float_round(-avg_price_unit * move.product_qty, precision_rounding=curr_rounding)
                    move.remaining_qty = 0
                    move.cumulated_value = move.product_id._get_latest_cumulated_value(not_move=move) + move.value
                    move.last_done_qty = move.product_id.qty_available
                elif move.product_id.cost_method == 'standard':
                    move.value = - move.product_id.standard_price * move.product_qty

        for move in res.filtered(lambda m: m.product_id.valuation == 'real_time'):
            move._account_entry_move()
        return res

    @api.multi
    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        if self.location_id.valuation_out_account_id:
            acc_src = self.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts_data['stock_input'].id

        if self.location_dest_id.valuation_in_account_id:
            acc_dest = self.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts_data['stock_output'].id

        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        if self._context.get('force_valuation_amount'):
            valuation_amount = self._context.get('force_valuation_amount')
        else:
            valuation_amount = cost

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(valuation_amount)

        # check that all data is correct
        if self.company_id.currency_id.is_zero(debit_value):
            if self.product_id.cost_method == 'standard':
                raise UserError(_("The found valuation amount for product %s is zero. Which means there is probably a configuration error. Check the costing method and the standard price") % (self.product_id.name,))
            return []
        credit_value = debit_value

        if self.product_id.cost_method == 'average' and self.company_id.anglo_saxon_accounting:
            # in case of a supplier return in anglo saxon mode, for products in average costing method, the stock_input
            # account books the real purchase price, while the stock account books the average price. The difference is
            # booked in the dedicated price difference account.
            if self.location_dest_id.usage == 'supplier' and self.origin_returned_move_id and self.origin_returned_move_id.purchase_line_id:
                debit_value = self.origin_returned_move_id.price_unit * qty
            # in case of a customer return in anglo saxon mode, for products in average costing method, the stock valuation
            # is made using the original average price to negate the delivery effect.
            if self.location_id.usage == 'customer' and self.origin_returned_move_id:
                debit_value = self.origin_returned_move_id.price_unit * qty
                credit_value = debit_value
        partner_id = (self.picking_id.partner_id and self.env['res.partner']._find_accounting_partner(self.picking_id.partner_id).id) or False
        debit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'debit': debit_value if debit_value > 0 else 0,
            'credit': -debit_value if debit_value < 0 else 0,
            'account_id': debit_account_id,
        }
        credit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'credit': credit_value if credit_value > 0 else 0,
            'debit': -credit_value if credit_value < 0 else 0,
            'account_id': credit_account_id,
        }
        res = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.product_id.property_account_creditor_price_difference
            if not price_diff_account:
                price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))
            price_diff_line = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': self.picking_id.name,
                'partner_id': partner_id,
                'credit': diff_amount > 0 and diff_amount or 0,
                'debit': diff_amount < 0 and -diff_amount or 0,
                'account_id': price_diff_account.id,
            }
            res.append((0, 0, price_diff_line))
        return res

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
        self.ensure_one()
        AccountMove = self.env['account.move']
        move_lines = self._prepare_account_move_line(self.product_qty, abs(self.value), credit_account_id, debit_account_id)
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': self.picking_id.name})
            new_account_move.post()

    def _account_entry_move(self):
        """ Accounting Valuation Entries """
        self.ensure_one()
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return False
        if self.restrict_partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return False

        location_from = self.location_id
        location_to = self.location_dest_id
        company_from = location_from.usage == 'internal' and location_from.company_id or False
        company_to = location_to and (location_to.usage == 'internal') and location_to.company_id or False

        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if company_to and (self.location_id.usage not in ('internal', 'transit') and self.location_dest_id.usage == 'internal' or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_from and location_from.usage == 'customer':  # goods returned from customer
                self.with_context(force_company=company_to.id)._create_account_move_line(acc_dest, acc_valuation, journal_id)
            else:
                self.with_context(force_company=company_to.id)._create_account_move_line(acc_src, acc_valuation, journal_id)

        # Create Journal Entry for products leaving the company
        if company_from and (self.location_id.usage == 'internal' and self.location_dest_id.usage not in ('internal', 'transit') or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_src, journal_id)
            else:
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_dest, journal_id)

        if self.company_id.anglo_saxon_accounting and self.location_id.usage == 'supplier' and self.location_dest_id.usage == 'customer':
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_src, acc_dest, journal_id)

    def _get_related_invoices(self): # To be overridden #TODO OCO: le faire dans sale et purchase (en ajoutant bien toujours au résultat du parent pour ménager l'héritage louche)
        return []

    def reconcile_valuation_with_invoices(self):
        for invoice in self._get_related_invoices():
            invoice.anglo_saxon_reconcile_valuation() #TODO OCO: devrait marcher, mais bien vérifier ça.


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.multi
    def _create_returns(self):
        new_picking_id, pick_type_id = super(StockReturnPicking, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        for move in new_picking.move_lines:
            return_picking_line = self.product_return_moves.filtered(lambda r: r.move_id == move.origin_returned_move_id)
            if return_picking_line and return_picking_line.to_refund:
                move.to_refund = True
        return new_picking_id, pick_type_id


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)", help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
