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
        if 'qty_done' in vals:
            # We need to update the `value`, `remaining_value` and `remaining_qty` on the linked
            # stock move.
            moves_to_update = {}
            for move_line in self.filtered(lambda ml: ml.state == 'done'):
                moves_to_update[move_line.move_id] = vals['qty_done'] - move_line.qty_done

            for move_id, qty_difference in moves_to_update.items():
                # more/less units are available, update `value`, `remaining_value` and
                # `remaining_qty` on the linked stock move.
                move_vals = {
                    'value': move_id.value + qty_difference * move_id.price_unit,
                    'remaining_value': move_id.remaining_value + qty_difference * move_id.price_unit,
                    'remaining_qty': move_id.remaining_qty + qty_difference,
                }
                move_id.write(move_vals)
                if move_id.product_id.valuation == 'real_time':
                    move_id.with_context(force_valuation_amount=qty_difference*move_id.price_unit)._account_entry_move()
        return super(StockMoveLine, self).write(vals)


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)",
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
    value = fields.Float()
    remaining_qty = fields.Float()
    remaining_value = fields.Float()
    account_move_ids = fields.One2many('account.move', 'stock_move_id')

    @api.multi
    def action_get_account_moves(self):
        self.ensure_one()
        action_ref = self.env.ref('account.action_move_journal_line')
        if not action_ref:
            return False
        action_data = action_ref.read()[0]
        action_data['domain'] = [('id', 'in', self.account_move_ids.ids)]
        return action_data

    def get_price_unit(self):
        """ Returns the unit price to store on the quant """
        return self.price_unit or self.product_id.standard_price

    @api.model
    def _get_in_base_domain(self, company_id=False):
        domain = [
            ('state', '=', 'done'),
            ('location_id.company_id', '=', False),
            ('location_dest_id.company_id', '=', company_id or self.env.user.company_id.id)
        ]
        return domain

    @api.model
    def _get_all_base_domain(self, company_id=False):
        domain = [
            ('state', '=', 'done'),
            '|',
                '&',
                    ('location_id.company_id', '=', False),
                    ('location_dest_id.company_id', '=', company_id or self.env.user.company_id.id),
                '&',
                    ('location_id.company_id', '=', company_id or self.env.user.company_id.id),
                    ('location_dest_id.company_id', '=', False)
        ]
        return domain

    def _get_in_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_in_base_domain(company_id=self.company_id.id)

    def _get_all_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_all_base_domain(company_id=self.company_id.id)

    def _is_in(self):
        """ Check if the move should be considered as entering the company so that the cost method
        will be able to apply the correct logic.

        :return: True if the move is entering the company else False
        """
        return not self.location_id.company_id and self.location_dest_id.company_id.id == self.company_id.id

    def _is_out(self):
        """ Check if the move should be considered as leaving the company so that the cost method
        will be able to apply the correct logic.

        :return: True if the move is leaving the company else False
        """
        return self.location_id.company_id.id == self.company_id.id and not self.location_dest_id.company_id

    @api.multi
    def action_done(self):
        self.product_price_update_before_done()
        res = super(StockMove, self).action_done()
        for move in res:
            if move._is_in():
                if move.product_id.cost_method in ['fifo', 'average']:
                    price_unit = move.price_unit or move.get_price_unit()
                    value = price_unit * move.product_qty
                    vals = {
                        'price_unit': price_unit,
                        'value': value,
                        'remaining_value': value,
                    }
                    if move.product_id.cost_method == 'fifo':
                        vals['remaining_qty'] = move.product_qty
                    move.write(vals)
                else:  # standard
                    move.write({
                        'price_unit': move.product_id.standard_price,
                        'value': move.product_id.standard_price * move.product_qty,
                    })
            elif move._is_out():
                if move.product_id.cost_method == 'fifo':
                    # Find back incoming stock moves (called candidates here) to value this move.
                    qty_to_take_on_candidates = move.product_qty
                    candidates = move.product_id._get_fifo_candidates_in_move()
                    new_standard_price = 0
                    tmp_value = 0  # to accumulate the value taken on the candidates
                    for candidate in candidates:
                        new_standard_price = candidate.price_unit
                        if candidate.remaining_qty <= qty_to_take_on_candidates:
                            qty_taken_on_candidate = candidate.remaining_qty
                        else:
                            qty_taken_on_candidate = qty_to_take_on_candidates

                        value_taken_on_candidate = qty_taken_on_candidate * candidate.price_unit
                        candidate_vals = {
                            'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                            'remaining_value': candidate.remaining_value - value_taken_on_candidate,
                        }
                        candidate.write(candidate_vals)

                        qty_to_take_on_candidates -= qty_taken_on_candidate
                        tmp_value += value_taken_on_candidate
                        if qty_to_take_on_candidates == 0:
                            break

                    # Update the standard price with the price of the last used candidate, if any.
                    if new_standard_price:
                        move.product_id.standard_price = new_standard_price

                    # If there's still quantity to value but we're out of candidates, we fall in the
                    # negative stock use case. We chose to value the out move at the price of the
                    # last out and a correction entry will be made once `_fifo_vacuum` is called.
                    if qty_to_take_on_candidates == 0:
                        move.write({
                            'value': -tmp_value,  # outgoing move are valued negatively
                            'price_unit': -tmp_value / move.product_qty,
                        })
                    elif qty_to_take_on_candidates > 0:
                        last_fifo_price = new_standard_price or move.product_id.standard_price
                        negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
                        vals = {
                            'remaining_qty': -qty_to_take_on_candidates,
                            'remaining_value': negative_stock_value,
                            'value': -tmp_value + negative_stock_value,
                            'price_unit': (-tmp_value + negative_stock_value) / move.product_qty,
                        }
                        move.write(vals)
                elif move.product_id.cost_method in ['standard', 'average']:
                    curr_rounding = move.company_id.currency_id.rounding
                    value = -float_round(move.product_id.standard_price * move.product_qty, precision_rounding=curr_rounding)
                    move.write({
                        'value': value,
                        'price_unit': value / move.product_qty,
                    })
        for move in res.filtered(lambda m: m.product_id.valuation == 'real_time'):
            move._account_entry_move()
        return res

    @api.multi
    def product_price_update_before_done(self):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self.filtered(lambda move: move.location_id.usage in ('supplier', 'production') and move.product_id.cost_method == 'average'):
            product_tot_qty_available = move.product_id.qty_available + tmpl_dict[move.product_id.id]

            if product_tot_qty_available == 0:
                new_std_price = move.get_price_unit()
            else:
                # Get the standard price
                amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.standard_price
                new_std_price = ((amount_unit * product_tot_qty_available) + (move.get_price_unit() * move.product_qty)) / (product_tot_qty_available + move.product_qty)

            tmpl_dict[move.product_id.id] += move.product_qty
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_context(force_company=move.company_id.id).sudo().write({'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

    @api.model
    def _fifo_vacuum(self):
        """ Every moves that need to be fixed are identifiable by having a negative `remaining_qty`.
        """
        # FIXME: sort by date (does filtered lose the order?)
        for move in self.filtered(lambda m: (m._is_in() or m._is_out()) and m.remaining_qty < 0):
            domain = [
                '|',
                    ('date', '>', move.date),
                    '&',
                        ('date', '=', move.date),
                        ('id', '>', move.id)
            ]
            domain += self._get_in_domain()
            candidates = self.search(domain, order='date, id')
            if not candidates:
                return
            qty_to_take_on_candidates = abs(move.remaining_qty)
            tmp_value = 0
            for candidate in candidates:
                if candidate.remaining_qty <= qty_to_take_on_candidates:
                    qty_taken_on_candidate = candidate.remaining_qty
                else:
                    qty_taken_on_candidate = qty_to_take_on_candidates

                value_taken_on_candidate = qty_taken_on_candidate * candidate.price_unit
                candidate_vals = {
                    'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                    'remaining_value': candidate.remaining_value - value_taken_on_candidate,
                }
                candidate.write(candidate_vals)

                qty_to_take_on_candidates -= qty_taken_on_candidate
                tmp_value += value_taken_on_candidate
                if qty_to_take_on_candidates == 0:
                    break

            corrected_value = move.remaining_value + tmp_value
            if move.product_id.valuation == 'real_time':
                if move._is_in():
                    # If we just compensated an IN move that has a negative remaining
                    # quantity, it means the move has returned more items than it received.
                    # The correction should behave as a return too. As `_account_entry_move`
                    # will post the natural values for an IN move (credit IN account, debit
                    # OUT one), we inverse the sign to create the correct entries.
                    move.with_context(force_valuation_amount=-corrected_value)._account_entry_move()
                else:
                    move.with_context(force_valuation_amount=corrected_value)._account_entry_move()

            if qty_to_take_on_candidates == 0:
                move.write({
                    'value': move.value - corrected_value,
                    'remaining_value': 0,
                    'remaining_qty': 0,
                })
            elif qty_to_take_on_candidates > 0:
                # It's possible that `remaining_value` is equals to 0 even if the move needs to be
                # compensated (negative stock for the first ever out in FIFO).
                move.write({
                    'value': move.value - corrected_value,
                    'remaining_value': 0 if not move.remaining_value else move.remaining_value + corrected_value,
                    'remaining_qty': -qty_to_take_on_candidates,
                })

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
                'ref': self.picking_id.name,
                'stock_move_id': self.id,
            })
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
