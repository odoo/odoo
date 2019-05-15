# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero

import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(string="Update quantities on SO/PO", copy=False,
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')
    value = fields.Float(copy=False)
    remaining_qty = fields.Float(copy=False)
    remaining_value = fields.Float(copy=False)
    account_move_ids = fields.One2many('account.move', 'stock_move_id')
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'stock_move_id')

    @api.multi
    def action_get_account_moves(self):
        self.ensure_one()
        action_ref = self.env.ref('account.action_move_journal_line')
        if not action_ref:
            return False
        action_data = action_ref.read()[0]
        action_data['domain'] = [('id', 'in', self.account_move_ids.ids)]
        return action_data

    def _get_price_unit(self):
        """ Returns the unit price to value this stock move """
        self.ensure_one()
        price_unit = self.price_unit
        # If the move is a return, use the original move's price unit.
        if self.origin_returned_move_id:
            price_unit = self.origin_returned_move_id.price_unit
        return not self.company_id.currency_id.is_zero(price_unit) and price_unit or self.product_id.standard_price

    @api.model
    def _get_in_base_domain(self, company_id=False):
        # Domain:
        # - state is done
        # - coming from a location without company, or an inventory location within the same company
        # - going to a location within the same company
        domain = [
            ('state', '=', 'done'),
            '&',
                '|',
                    ('location_id.company_id', '=', False),
                    '&',
                        ('location_id.usage', 'in', ['inventory', 'production']),
                        ('location_id.company_id', '=', company_id or self.env.company.id),
                ('location_dest_id.company_id', '=', company_id or self.env.company.id),
        ]
        return domain

    @api.model
    def _get_all_base_domain(self, company_id=False):
        # Domain:
        # - state is done
        # Then, either 'in' or 'out' moves.
        # 'in' moves:
        # - coming from a location without company, or an inventory location within the same company
        # - going to a location within the same company
        # 'out' moves:
        # - coming from to a location within the same company
        # - going to a location without company, or an inventory location within the same company
        domain = [
            ('state', '=', 'done'),
            '|',
                '&',
                    '|',
                        ('location_id.company_id', '=', False),
                        '&',
                            ('location_id.usage', 'in', ['inventory', 'production']),
                            ('location_id.company_id', '=', company_id or self.env.company.id),
                    ('location_dest_id.company_id', '=', company_id or self.env.company.id),
                '&',
                    ('location_id.company_id', '=', company_id or self.env.company.id),
                    '|',
                        ('location_dest_id.company_id', '=', False),
                        '&',
                            ('location_dest_id.usage', '=', 'inventory'),
                            ('location_dest_id.company_id', '=', company_id or self.env.company.id),
        ]
        return domain

    def _get_in_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_in_base_domain(company_id=self.company_id.id)

    def _get_all_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_all_base_domain(company_id=self.company_id.id)

    @api.model
    def _get_valued_types(self):
        """Returns a list of `valued_type` as strings. During `action_done`, we'll call
        `_is_[valued_type]'. If the result of this method is truthy, we'll consider the move to be
        valued.

        :returns: a list of `valued_type`
        :rtype: list
        """
        return ['in', 'out', 'dropshipped', 'dropshipped_returned']

    def _get_in_move_lines(self):
        """ Returns the `stock.move.line` records of `self` considered as incoming. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the incoming records
        :rtype: recordset
        """
        self.ensure_one()
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                continue
            if not move_line.location_id._should_be_valued() and move_line.location_dest_id._should_be_valued():
                res |= move_line
        return res

    def _is_in(self):
        """Check if the move should be considered as entering the company so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is entering the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_in_move_lines():
            return True
        return False

    def _get_out_move_lines(self):
        """ Returns the `stock.move.line` records of `self` considered as outgoing. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the outgoing records
        :rtype: recordset
        """
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                continue
            if move_line.location_id._should_be_valued() and not move_line.location_dest_id._should_be_valued():
                res |= move_line
        return res

    def _is_out(self):
        """Check if the move should be considered as leaving the company so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is leaving the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_out_move_lines():
            return True
        return False

    def _is_dropshipped(self):
        """Check if the move should be considered as a dropshipping move so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is a dropshipping one else False
        :rtype: bool
        """
        self.ensure_one()
        return self.location_id.usage == 'supplier' and self.location_dest_id.usage == 'customer'

    def _is_dropshipped_returned(self):
        """Check if the move should be considered as a returned dropshipping move so that the cost
        method will be able to apply the correct logic.

        :returns: True if the move is a returned dropshipping one else False
        :rtype: bool
        """
        self.ensure_one()
        return self.location_id.usage == 'customer' and self.location_dest_id.usage == 'supplier'

    def _prepare_common_svl_vals(self):
        """When a `stock.valuation.layer` is created from a `stock.move`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move`
        :rtype: dict
        """
        self.ensure_one()
        return {
            'stock_move_id': self.id,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'description': self.name,
        }

    def _create_in_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            if move.product_id.cost_method == 'standard':
                unit_cost = move.product_id.standard_price
            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].create(svl_vals_list)

    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            valued_move_lines = move._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].create(svl_vals_list)


    @api.model
    def _run_fifo(self, move, quantity=None):
        """ Value `move` according to the FIFO rule, meaning we consume the
        oldest receipt first. Candidates receipts are marked consumed or free
        thanks to their `remaining_qty` and `remaining_value` fields.
        By definition, `move` should be an outgoing stock move.

        :param quantity: quantity to value instead of `move.product_qty`
        :returns: valued amount in absolute
        """
        move.ensure_one()

        # Deal with possible move lines that do not impact the valuation.
        valued_move_lines = move.move_line_ids.filtered(lambda ml: ml.location_id._should_be_valued() and not ml.location_dest_id._should_be_valued() and not ml.owner_id)
        valued_quantity = 0
        for valued_move_line in valued_move_lines:
            valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)

        # Find back incoming stock moves (called candidates here) to value this move.
        qty_to_take_on_candidates = quantity or valued_quantity
        candidates = move.product_id._get_fifo_candidates_in_move_with_company(move.company_id.id)
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        for candidate in candidates:
            new_standard_price = candidate.price_unit
            if candidate.remaining_qty <= qty_to_take_on_candidates:
                qty_taken_on_candidate = candidate.remaining_qty
            else:
                qty_taken_on_candidate = qty_to_take_on_candidates

            # As applying a landed cost do not update the unit price, naivelly doing
            # something like qty_taken_on_candidate * candidate.price_unit won't make
            # the additional value brought by the landed cost go away.
            candidate_price_unit = candidate.remaining_value / candidate.remaining_qty
            value_taken_on_candidate = qty_taken_on_candidate * candidate_price_unit
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
        if new_standard_price and move.product_id.cost_method == 'fifo':
            move.product_id.sudo().with_context(force_company=move.company_id.id) \
                .standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        if qty_to_take_on_candidates == 0:
            move.write({
                'value': -tmp_value if not quantity else move.value or -tmp_value,  # outgoing move are valued negatively
                'price_unit': -tmp_value / (move.product_qty or quantity),
            })
        elif qty_to_take_on_candidates > 0:
            last_fifo_price = new_standard_price or move.product_id.standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': move.remaining_qty + -qty_to_take_on_candidates,
                'remaining_value': move.remaining_value + negative_stock_value,
                'value': -tmp_value,
                'price_unit': -1 * last_fifo_price,
            }
            move.write(vals)
        return tmp_value

    def _run_valuation(self, quantity=None):
        self.ensure_one()
        value_to_return = 0
        if self._is_in():
            valued_move_lines = self._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, self.product_id.uom_id)

            # Note: we always compute the fifo `remaining_value` and `remaining_qty` fields no
            # matter which cost method is set, to ease the switching of cost method.
            vals = {}
            price_unit = self._get_price_unit()
            value = price_unit * (quantity or valued_quantity)
            value_to_return = value if quantity is None or not self.value else self.value
            vals = {
                'price_unit': price_unit,
                'value': value_to_return,
                'remaining_value': value if quantity is None else self.remaining_value + value,
            }
            vals['remaining_qty'] = valued_quantity if quantity is None else self.remaining_qty + quantity

            if self.product_id.cost_method == 'standard':
                value = self.product_id.standard_price * (quantity or valued_quantity)
                value_to_return = value if quantity is None or not self.value else self.value
                vals.update({
                    'price_unit': self.product_id.standard_price,
                    'value': value_to_return,
                })
            self.write(vals)
        elif self._is_out():
            valued_move_lines = self._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, self.product_id.uom_id)
            self.env['stock.move']._run_fifo(self, quantity=quantity)
            if self.product_id.cost_method in ['standard', 'average']:
                curr_rounding = self.company_id.currency_id.rounding
                value = -float_round(self.product_id.standard_price * (valued_quantity if quantity is None else quantity), precision_rounding=curr_rounding)
                value_to_return = value if quantity is None else self.value + value
                self.write({
                    'value': value_to_return,
                    'price_unit': value / valued_quantity,
                })
        elif self._is_dropshipped() or self._is_dropshipped_returned():
            curr_rounding = self.company_id.currency_id.rounding
            if self.product_id.cost_method in ['fifo']:
                price_unit = self._get_price_unit()
                # see test_dropship_fifo_perpetual_anglosaxon_ordered
                self.product_id.standard_price = price_unit
            else:
                price_unit = self.product_id.standard_price
            value = float_round(self.product_qty * price_unit, precision_rounding=curr_rounding)
            value_to_return = value if self._is_dropshipped() else -value
            # In move have a positive value, out move have a negative value, let's arbitrary say
            # dropship are positive.
            self.write({
                'value': value_to_return,
                'price_unit': price_unit if self._is_dropshipped() else -price_unit,
            })
        return value_to_return

    def _action_done(self, cancel_backorder=False):
        # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
        valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
        for move in self:
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move
                    continue

        # AVCO application
        valued_moves['in'].product_price_update_before_done()

        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

        stock_valuation_layers = self.env['stock.valuation.layer']
        # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
        for valued_type in self._get_valued_types():
            todo_valued_moves = valued_moves[valued_type]
            if todo_valued_moves:
                todo_valued_moves._sanity_check_for_valuation()
                stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()
                continue

        for stock_valuation_layer in stock_valuation_layers:
            if not stock_valuation_layer.product_id.valuation == 'real_time':
                continue
            stock_valuation_layer.stock_move_id.with_context(svl_id=stock_valuation_layer.id, force_valuation_amount=abs(stock_valuation_layer.value), forced_quantity=stock_valuation_layer.quantity)._account_entry_move()
        return res

    def _sanity_check_for_valuation(self):
        for move in self:
            # Apply restrictions on the stock move to be able to make
            # consistent accounting entries.
            if move._is_in() and move._is_out():
                raise UserError(_("The move lines are not in a consistent state: some are entering and other are leaving the company."))
            company_src = move.mapped('move_line_ids.location_id.company_id')
            company_dst = move.mapped('move_line_ids.location_dest_id.company_id')
            try:
                if company_src:
                    company_src.ensure_one()
                if company_dst:
                    company_dst.ensure_one()
            except ValueError:
                raise UserError(_("The move lines are not in a consistent states: they do not share the same origin or destination company."))
            if company_src and company_dst and company_src.id != company_dst.id:
                raise UserError(_("The move lines are not in a consistent states: they are doing an intercompany in a single step while they should go through the intercompany transit location."))

    @api.multi
    def product_price_update_before_done(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self.filtered(lambda move: move._is_in() and move.product_id.cost_method == 'average'):
            product_tot_qty_available = move.product_id.quantity_svl + tmpl_dict[move.product_id.id]
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)

            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty_done, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
            else:
                # Get the standard price
                amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.standard_price
                qty = forced_qty or qty_done
                new_std_price = ((amount_unit * product_tot_qty_available) + (move._get_price_unit() * qty)) / (product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_context(force_company=move.company_id.id).sudo().write({'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

    @api.model
    def _fifo_vacuum(self):
        """ Every moves that need to be fixed are identifiable by having a negative `remaining_qty`.
        """
        for move in self.filtered(lambda m: (m._is_in() or m._is_out()) and m.remaining_qty < 0):
            domain = [
                ('remaining_qty', '>', 0),
                '|',
                    ('date', '>', move.date),
                    '&',
                        ('date', '=', move.date),
                        ('id', '>', move.id)
            ]
            domain += move._get_in_domain()
            candidates = self.search(domain, order='date, id')
            if not candidates:
                continue
            qty_to_take_on_candidates = abs(move.remaining_qty)
            qty_taken_on_candidates = 0
            tmp_value = 0
            for candidate in candidates:
                if candidate.remaining_qty <= qty_to_take_on_candidates:
                    qty_taken_on_candidate = candidate.remaining_qty
                else:
                    qty_taken_on_candidate = qty_to_take_on_candidates
                qty_taken_on_candidates += qty_taken_on_candidate

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


            # When working with `price_unit`, beware that out move are negative.
            move_price_unit = move.price_unit if move._is_out() else -1 * move.price_unit
            # Get the estimated value we will correct.
            remaining_value_before_vacuum = qty_taken_on_candidates * move_price_unit
            new_remaining_qty = move.remaining_qty + qty_taken_on_candidates
            new_remaining_value = new_remaining_qty * abs(move.price_unit)

            corrected_value = remaining_value_before_vacuum + tmp_value
            move.write({
                'remaining_value': new_remaining_value,
                'remaining_qty': new_remaining_qty,
                'value': move.value - corrected_value,
            })

            if move.product_id.valuation == 'real_time':
                # If `corrected_value` is 0, absolutely do *not* call `_account_entry_move`. We
                # force the amount in the context, but in the case it is 0 it'll create an entry
                # for the entire cost of the move. This case happens when the candidates moves
                # entirely compensate the problematic move.
                if move.company_id.currency_id.is_zero(corrected_value):
                    continue

                if move._is_in():
                    # If we just compensated an IN move that has a negative remaining
                    # quantity, it means the move has returned more items than it received.
                    # The correction should behave as a return too. As `_account_entry_move`
                    # will post the natural values for an IN move (credit IN account, debit
                    # OUT one), we inverse the sign to create the correct entries.
                    move.with_context(force_valuation_amount=-corrected_value, forced_quantity=0)._account_entry_move()
                else:
                    move.with_context(force_valuation_amount=corrected_value, forced_quantity=0)._account_entry_move()

    @api.model
    def _run_fifo_vacuum(self):
        # Call `_fifo_vacuum` on concerned moves
        fifo_valued_products = self.env['product.product']
        fifo_valued_categories = self.env['product.category'].search([('property_cost_method', '=', 'fifo')])
        fifo_valued_products |= self.env['product.product'].search([('categ_id', 'child_of', fifo_valued_categories.ids)])
        moves_to_vacuum = self.search(
            [('product_id', 'in', fifo_valued_products.ids), ('remaining_qty', '<', 0)] + self._get_all_base_domain())
        moves_to_vacuum._fifo_vacuum()

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
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts.'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.display_name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.display_name))
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
        if self.company_id.currency_id.is_zero(debit_value) and not self.env['ir.config_parameter'].sudo().get_param('stock_account.allow_zero_cost'):
            raise UserError(_("The cost of %s is currently equal to 0. Change the cost or the configuration of your product to avoid an incorrect valuation.") % (self.product_id.display_name,))
        credit_value = debit_value


        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        res = [(0, 0, line_vals) for line_vals in self._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id).values()]

        return res

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id):
        # This method returns a dictonary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()

        if self._context.get('forced_ref'):
            ref = self._context['forced_ref']
        else:
            ref = self.picking_id.name

        debit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': ref,
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
            'ref': ref,
            'partner_id': partner_id,
            'credit': credit_value if credit_value > 0 else 0,
            'debit': -credit_value if credit_value < 0 else 0,
            'account_id': credit_account_id,
        }

        rslt = {'credit_line_vals': credit_line_vals, 'debit_line_vals': debit_line_vals}
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.product_id.property_account_creditor_price_difference

            if not price_diff_account:
                price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))

            rslt['price_diff_line_vals'] = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': ref,
                'partner_id': partner_id,
                'credit': diff_amount > 0 and diff_amount or 0,
                'debit': diff_amount < 0 and -diff_amount or 0,
                'account_id': price_diff_account.id,
            }
        return rslt

    def _get_partner_id_for_valuation_lines(self):
        return (self.picking_id.partner_id and self.env['res.partner']._find_accounting_partner(self.picking_id.partner_id).id) or False

    def _prepare_move_split_vals(self, uom_qty):
        vals = super(StockMove, self)._prepare_move_split_vals(uom_qty)
        vals['to_refund'] = self.to_refund
        return vals

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
        self.ensure_one()
        AccountMove = self.env['account.move']
        quantity = self.env.context.get('forced_quantity', self.product_qty)
        quantity = quantity if self._is_in() else -1 * quantity

        # Make an informative `ref` on the created account move to differentiate between classic
        # movements, vacuum and edition of past moves.
        ref = self.picking_id.name
        if self.env.context.get('force_valuation_amount'):
            if self.env.context.get('forced_quantity') == 0:
                ref = 'Revaluation of %s (negative inventory)' % ref
            elif self.env.context.get('forced_quantity') is not None:
                ref = 'Correction of %s (modification of past move)' % ref
        if not ref and self.inventory_id:
            ref = self.inventory_id.name

        move_lines = self.with_context(forced_ref=ref)._prepare_account_move_line(quantity, abs(self.value), credit_account_id, debit_account_id)
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.sudo().create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': ref,
                'stock_move_id': self.id,
            })
            if self.env.context.get('svl_id'):
                new_account_move['stock_valuation_layer_ids'] = [(6, None, [self.env.context.get('svl_id')])]
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
        company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
        company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False

        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if self._is_in():
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_from and location_from.usage == 'customer':  # goods returned from customer
                self.with_context(force_company=company_to.id)._create_account_move_line(acc_dest, acc_valuation, journal_id)
            else:
                self.with_context(force_company=company_to.id)._create_account_move_line(acc_src, acc_valuation, journal_id)

        # Create Journal Entry for products leaving the company
        if self._is_out():
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_src, journal_id)
            else:
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_dest, journal_id)

        if self.company_id.anglo_saxon_accounting:
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if self._is_dropshipped():
                self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_src, acc_dest, journal_id)
            elif self._is_dropshipped_returned():
                self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_dest, acc_src, journal_id)

        if self.company_id.anglo_saxon_accounting:
            #eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
            self._get_related_invoices()._anglo_saxon_reconcile_valuation(product=self.product_id)

    def _get_related_invoices(self): # To be overridden in purchase and sale_stock
        """ This method is overrided in both purchase and sale_stock modules to adapt
        to the way they mix stock moves with invoices.
        """
        return self.env['account.invoice']

