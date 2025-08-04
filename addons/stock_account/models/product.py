# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import float_is_zero, float_repr, float_round, float_compare
from odoo.exceptions import ValidationError
from collections import defaultdict
from datetime import datetime


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cost_method = fields.Selection(
        string="Cost Method",
        selection=[
            ('standard', "Standard Price"),
            ('fifo', "First In First Out (FIFO)"),
            ('average', "Average Cost (AVCO)"),
        ],
        compute='_compute_cost_method',
    )
    valuation = fields.Selection(
        string="Valuation",
        selection=[
            ('periodic', 'Periodic (at closing)'),
            ('real_time', 'Perpetual (at invoicing)'),
        ],
        compute='_compute_valuation',
    )
    lot_valuated = fields.Boolean(
        string="Valuation by Lot/Serial",
        compute='_compute_lot_valuated', store=True, readonly=False,
        help="If checked, the valuation will be specific by Lot/Serial number.",
    )
    property_price_difference_account_id = fields.Many2one(
        'account.account', 'Price Difference Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""With perpetual valuation, this account will hold the price difference between the standard price and the bill price.""")

    @api.depends('tracking')
    def _compute_lot_valuated(self):
        for product in self:
            if product.tracking == 'none':
                product.lot_valuated = False

    @api.depends_context('company')
    @api.depends('categ_id.property_cost_method')
    def _compute_cost_method(self):
        for product_template in self:
            product_template.cost_method = (
                product_template.categ_id.with_company(
                    product_template.company_id
                ).property_cost_method
                or (product_template.company_id or self.env.company).cost_method
            )

    @api.depends_context('company')
    @api.depends('categ_id.property_valuation')
    def _compute_valuation(self):
        pt_with_category = self.filtered('categ_id')
        (self - pt_with_category).valuation = 'periodic'
        for product_template in pt_with_category:
            product_template.valuation = product_template.categ_id.with_company(
                product_template.company_id
            ).property_valuation

    # -------------------------------------------------------------------------
    # Misc.
    # -------------------------------------------------------------------------
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super()._get_product_accounts()
        AccountAccount = self.env['account.account']

        accounts['stock_valuation'] = (
                self.categ_id.property_stock_valuation_account_id
                or self.categ_id._fields['property_stock_valuation_account_id'].get_company_dependent_fallback(self.categ_id)
                or AccountAccount
            )
        accounts['stock_variation'] = accounts['stock_valuation'].account_stock_variation_id
        return accounts

    def get_product_accounts(self, fiscal_pos=None):
        """ Add the stock journal related to product to the result of super()
        @return: dictionary which contains all needed information regarding stock accounts and journal and super (income+expense accounts)
        """
        accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)
        accounts.update({
            'stock_journal': (
                self.categ_id.property_stock_journal
                or self.categ_id._fields['property_stock_journal'].get_company_dependent_fallback(self.categ_id)
            )
        })
        return accounts


class ProductProduct(models.Model):
    _inherit = 'product.product'

    avg_cost = fields.Monetary(
        string="Average Cost", compute='_compute_value',
        compute_sudo=True, currency_field='company_currency_id')
    total_value = fields.Monetary(
        string="Total Value", compute='_compute_value',
        compute_sudo=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one(
        'res.currency', 'Valuation Currency', compute='_compute_value', compute_sudo=True,
        help="Technical field to correctly show the currently selected company's currency that corresponds "
             "to the totaled value of the product's valuation layers")

    @api.depends_context('to_date', 'company')
    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id

        for product in self:
            at_date = product.env.context.get('to_date')
            qty_available = product.sudo(False).qty_available
            if product.cost_method == 'standard':
                product.total_value = product.standard_price * qty_available
            elif product.cost_method == 'average':
                product.total_value = product._run_avco(at_date=at_date)[1]
            else:
                product.total_value = product._run_fifo(qty_available, at_date=at_date)
            product.avg_cost = product.total_value / qty_available if qty_available else 0.0

    def write(self, vals):
        old_price = False
        if 'standard_price' in vals and not self.env.context.get('disable_auto_revaluation'):
            old_price = {product: product.standard_price for product in self}
        if 'lot_valuated' in vals:
            # lot_valuated must be updated from the ProductTemplate
            self.product_tmpl_id.write({'lot_valuated': vals.pop('lot_valuated')})
        res = super().write(vals)
        if old_price:
            self._change_standard_price(old_price)
        return res

    # -------------------------------------------------------------------------
    # Private
    # -------------------------------------------------------------------------

    def _change_standard_price(self, old_price):
        for product in self:
            if product.cost_method == 'fifo' or product.standard_price == old_price.get(product):
                continue
            self.env['product.value'].sudo().create({
                'product_id': product.id,
<<<<<<< 9ab3f4e4e70f501e4d2acaf2ffab8531c667b9e2
                'value': product.standard_price,
                'company_id': product.company_id.id or self.env.company.id,
                'date': fields.Datetime.now(),
                'description': _('Price update from %(old_price)s to %(new_price)s by %(user)s',
                    old_price=old_price, new_price=product.standard_price, user=self.env.user.name)
||||||| 995a7072cb3315fc03544b281b1ed5ca4e81e901
                'description': _(
                    'Product value manually modified (from %(original_price)s to %(new_price)s)',
                    original_price=product.standard_price,
                    new_price=rounded_new_price,
                ),
                'value': value,
                'quantity': 0,
            }
            svl_vals_list.append(svl_vals)
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
        stock_valuation_layers._change_standart_price_accounting_entries(new_price)

    def _get_fifo_candidates_domain(self, company, lot=False):
        return [
            ("product_id", "=", self.id),
            ("remaining_qty", ">", 0),
            ("company_id", "=", company.id),
            ("lot_id", "=", lot.id if lot else False),
        ]

    def _get_fifo_candidates(self, company, lot=False):
        candidates_domain = self._get_fifo_candidates_domain(company, lot=lot)
        return self.env["stock.valuation.layer"].sudo().search(candidates_domain).sorted(lambda svl: svl._candidate_sort_key())

    def _get_qty_taken_on_candidate(self, qty_to_take_on_candidates, candidate):
        return min(qty_to_take_on_candidates, candidate.remaining_qty)

    def _run_fifo(self, quantity, company, lot=False):
        self.ensure_one()

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        candidates = self._get_fifo_candidates(company, lot=lot)
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        for candidate in candidates:
            qty_taken_on_candidate = self._get_qty_taken_on_candidate(qty_to_take_on_candidates, candidate)

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
            new_standard_price = candidate_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
            new_remaining_value = candidate.remaining_value - value_taken_on_candidate

            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value,
            }

            candidate.write(candidate_vals)

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate

            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                    next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                    new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
                break

        # Fifo out will change the AVCO value of the product. So in case of out,
        # we recompute it base on the remaining value and quantities.
        if self.cost_method == 'fifo':
            quantity_svl = sum(candidates.mapped('remaining_qty'))
            value_svl = sum(candidates.mapped('remaining_value'))
            product = self.sudo().with_company(company.id).with_context(disable_auto_svl=True)
            if float_compare(quantity_svl, 0.0, precision_rounding=self.uom_id.rounding) > 0:
                product.standard_price = value_svl / quantity_svl
            elif candidates and not float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                product.standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            vals = {
                'value': -tmp_value,
                'unit_cost': tmp_value / quantity,
            }
        else:
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': -qty_to_take_on_candidates,
                'value': -tmp_value,
                'unit_cost': last_fifo_price,
            }
        return vals

    def _run_fifo_vacuum(self, company=None):
        """Compensate layer valued at an estimated price with the price of future receipts
        if any. If the estimated price is equals to the real price, no layer is created but
        the original layer is marked as compensated.

        :param company: recordset of `res.company` to limit the execution of the vacuum
        """
        if company is None:
            company = self.env.company
        ValuationLayer = self.env['stock.valuation.layer'].sudo()
        svls_to_vacuum_by_product = defaultdict(lambda: ValuationLayer)
        res = ValuationLayer._read_group([
            ('product_id', 'in', self.ids),
            ('remaining_qty', '<', 0),
            ('stock_move_id', '!=', False),
            ('company_id', '=', company.id),
        ], ['product_id'], ['id:recordset', 'create_date:min'], order='create_date:min')
        min_create_date = datetime.max
        if not res:
            return
        for group in res:
            svls_to_vacuum_by_product[group[0].id] = group[1].sorted(key=lambda r: (r.create_date, r.id))
            min_create_date = min(min_create_date, group[2])
        all_candidates_by_product = defaultdict(lambda: ValuationLayer)
        lot_to_update = []
        res = ValuationLayer._read_group([
            ('product_id', 'in', self.ids),
            ('remaining_qty', '>', 0),
            ('company_id', '=', company.id),
            ('create_date', '>=', min_create_date),
        ], ['product_id'], ['id:recordset'])
        for group in res:
            all_candidates_by_product[group[0].id] = group[1]

        new_svl_vals_real_time = []
        new_svl_vals_manual = []
        real_time_svls_to_vacuum = ValuationLayer

        for product in self.with_company(company.id):
            all_candidates = all_candidates_by_product[product.id]
            current_real_time_svls = ValuationLayer
            for svl_to_vacuum in svls_to_vacuum_by_product[product.id]:
                # We don't use search to avoid executing _flush_search and to decrease interaction with DB
                candidates = all_candidates.filtered(
                    lambda r: r.create_date > svl_to_vacuum.create_date
                    or r.create_date == svl_to_vacuum.create_date
                    and r.id > svl_to_vacuum.id
                )
                if product.lot_valuated:
                    candidates = candidates.filtered(lambda r: r.lot_id == svl_to_vacuum.lot_id)
                if not candidates:
                    break
                qty_to_take_on_candidates = abs(svl_to_vacuum.remaining_qty)
                qty_taken_on_candidates = 0
                tmp_value = 0
                for candidate in candidates:
                    qty_taken_on_candidate = min(candidate.remaining_qty, qty_to_take_on_candidates)
                    qty_taken_on_candidates += qty_taken_on_candidate

                    candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
                    value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                    value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                    new_remaining_value = candidate.remaining_value - value_taken_on_candidate

                    candidate_vals = {
                        'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                        'remaining_value': new_remaining_value
                    }
                    candidate.write(candidate_vals)
                    if not (candidate.remaining_qty > 0):
                        all_candidates -= candidate

                    qty_to_take_on_candidates -= qty_taken_on_candidate
                    tmp_value += value_taken_on_candidate
                    if float_is_zero(qty_to_take_on_candidates, precision_rounding=product.uom_id.rounding):
                        break

                # Get the estimated value we will correct.
                remaining_value_before_vacuum = svl_to_vacuum.unit_cost * qty_taken_on_candidates
                new_remaining_qty = svl_to_vacuum.remaining_qty + qty_taken_on_candidates
                corrected_value = remaining_value_before_vacuum - tmp_value
                svl_to_vacuum.write({
                    'remaining_qty': new_remaining_qty,
                })

                # Don't create a layer or an accounting entry if the corrected value is zero.
                if svl_to_vacuum.currency_id.is_zero(corrected_value):
                    continue

                corrected_value = svl_to_vacuum.currency_id.round(corrected_value)

                move = svl_to_vacuum.stock_move_id
                new_svl_vals = new_svl_vals_real_time if product.valuation == 'real_time' else new_svl_vals_manual
                new_svl_vals.append({
                    'product_id': product.id,
                    'value': corrected_value,
                    'unit_cost': 0,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'stock_move_id': move.id,
                    'company_id': move.company_id.id,
                    'description': 'Revaluation of %s (negative inventory)' % (move.picking_id.name or move.name),
                    'stock_valuation_layer_id': svl_to_vacuum.id,
                    'lot_id': svl_to_vacuum.lot_id.id,
                })
                lot_to_update.append(svl_to_vacuum.lot_id)
                if product.valuation == 'real_time':
                    current_real_time_svls |= svl_to_vacuum
            real_time_svls_to_vacuum |= current_real_time_svls
        ValuationLayer.create(new_svl_vals_manual)
        vacuum_svls = ValuationLayer.create(new_svl_vals_real_time)

        # If some negative stock were fixed, we need to recompute the standard price.
        for product in self:
            product = product.with_company(company.id)
            if not svls_to_vacuum_by_product[product.id]:
                continue
            if product.cost_method not in ['average', 'fifo'] or float_is_zero(product.quantity_svl,
                                                                      precision_rounding=product.uom_id.rounding):
                continue
            if product.lot_valuated:
                for lot in lot_to_update:
                    if float_is_zero(lot.quantity_svl, precision_rounding=product.uom_id.rounding):
                        continue
                    lot.sudo().with_context(disable_auto_svl=True).write(
                        {'standard_price': lot.value_svl / lot.quantity_svl}
                    )
            product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl})

        vacuum_svls._validate_accounting_entries()
        self._create_fifo_vacuum_anglo_saxon_expense_entries(zip(vacuum_svls, real_time_svls_to_vacuum))

    @api.model
    def _create_fifo_vacuum_anglo_saxon_expense_entries(self, vacuum_pairs):
        """ Batch version of _create_fifo_vacuum_anglo_saxon_expense_entry
        """
        AccountMove = self.env['account.move'].sudo()
        account_move_vals = []
        vacuum_pairs_to_reconcile = []
        svls_accounts = {}
        for vacuum_svl, svl_to_vacuum in vacuum_pairs:
            if not vacuum_svl.company_id.anglo_saxon_accounting or not svl_to_vacuum.stock_move_id._is_out():
                continue
            account_move_lines = svl_to_vacuum.account_move_id.line_ids
            # Find related customer invoice where product is delivered while you don't have units in stock anymore
            reconciled_line_ids = list(set(account_move_lines._reconciled_lines()) - set(account_move_lines.ids))
            account_move = AccountMove.search([('line_ids', 'in', reconciled_line_ids)], limit=1)
            # If delivered quantity is not invoiced then no need to create this entry
            if not account_move:
                continue
            accounts = svl_to_vacuum.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=account_move.fiscal_position_id)
            if not accounts.get('stock_output') or not accounts.get('expense'):
                continue
            svls_accounts[svl_to_vacuum.id] = accounts
            description = "Expenses %s" % (vacuum_svl.description)
            move_lines = vacuum_svl.stock_move_id._prepare_account_move_line(
            vacuum_svl.quantity, vacuum_svl.value * -1,
            accounts['stock_output'].id, accounts['expense'].id,
            vacuum_svl.id, description)
            account_move_vals.append({
                'journal_id': accounts['stock_journal'].id,
                'line_ids': move_lines,
                'date': self._context.get('force_period_date', fields.Date.context_today(self)),
                'ref': description,
                'stock_move_id': vacuum_svl.stock_move_id.id,
                'move_type': 'entry',
=======
                'description': _(
                    'Product value manually modified (from %(original_price)s to %(new_price)s)',
                    original_price=product.standard_price,
                    new_price=rounded_new_price,
                ),
                'value': value,
                'quantity': 0,
            }
            svl_vals_list.append(svl_vals)
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
        stock_valuation_layers._change_standart_price_accounting_entries(new_price)

    def _get_fifo_candidates_domain(self, company, lot=False):
        return [
            ("product_id", "=", self.id),
            ("remaining_qty", ">", 0),
            ("company_id", "=", company.id),
            ("lot_id", "=", lot.id if lot else False),
        ]

    def _get_fifo_candidates(self, company, lot=False):
        candidates_domain = self._get_fifo_candidates_domain(company, lot=lot)
        return self.env["stock.valuation.layer"].sudo().search(candidates_domain)

    def _get_qty_taken_on_candidate(self, qty_to_take_on_candidates, candidate):
        return min(qty_to_take_on_candidates, candidate.remaining_qty)

    def _run_fifo(self, quantity, company, lot=False):
        self.ensure_one()

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        candidates = self._get_fifo_candidates(company, lot=lot)
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        for candidate in candidates:
            qty_taken_on_candidate = self._get_qty_taken_on_candidate(qty_to_take_on_candidates, candidate)

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
            new_standard_price = candidate_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
            new_remaining_value = candidate.remaining_value - value_taken_on_candidate

            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value,
            }

            candidate.write(candidate_vals)

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate

            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                    next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                    new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
                break

        # Fifo out will change the AVCO value of the product. So in case of out,
        # we recompute it base on the remaining value and quantities.
        if self.cost_method == 'fifo':
            quantity_svl = sum(candidates.mapped('remaining_qty'))
            value_svl = sum(candidates.mapped('remaining_value'))
            product = self.sudo().with_company(company.id).with_context(disable_auto_svl=True)
            if float_compare(quantity_svl, 0.0, precision_rounding=self.uom_id.rounding) > 0:
                product.standard_price = value_svl / quantity_svl
            elif candidates and not float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                product.standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            vals = {
                'value': -tmp_value,
                'unit_cost': tmp_value / quantity,
            }
        else:
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': -qty_to_take_on_candidates,
                'value': -tmp_value,
                'unit_cost': last_fifo_price,
            }
        return vals

    def _run_fifo_vacuum(self, company=None):
        """Compensate layer valued at an estimated price with the price of future receipts
        if any. If the estimated price is equals to the real price, no layer is created but
        the original layer is marked as compensated.

        :param company: recordset of `res.company` to limit the execution of the vacuum
        """
        if company is None:
            company = self.env.company
        ValuationLayer = self.env['stock.valuation.layer'].sudo()
        svls_to_vacuum_by_product = defaultdict(lambda: ValuationLayer)
        res = ValuationLayer._read_group([
            ('product_id', 'in', self.ids),
            ('remaining_qty', '<', 0),
            ('stock_move_id', '!=', False),
            ('company_id', '=', company.id),
        ], ['product_id'], ['id:recordset', 'create_date:min'], order='create_date:min')
        min_create_date = datetime.max
        if not res:
            return
        for group in res:
            svls_to_vacuum_by_product[group[0].id] = group[1].sorted(key=lambda r: (r.create_date, r.id))
            min_create_date = min(min_create_date, group[2])
        all_candidates_by_product = defaultdict(lambda: ValuationLayer)
        lot_to_update = []
        res = ValuationLayer._read_group([
            ('product_id', 'in', self.ids),
            ('remaining_qty', '>', 0),
            ('company_id', '=', company.id),
            ('create_date', '>=', min_create_date),
        ], ['product_id'], ['id:recordset'])
        for group in res:
            all_candidates_by_product[group[0].id] = group[1]

        new_svl_vals_real_time = []
        new_svl_vals_manual = []
        real_time_svls_to_vacuum = ValuationLayer

        for product in self.with_company(company.id):
            all_candidates = all_candidates_by_product[product.id]
            current_real_time_svls = ValuationLayer
            for svl_to_vacuum in svls_to_vacuum_by_product[product.id]:
                # We don't use search to avoid executing _flush_search and to decrease interaction with DB
                candidates = all_candidates.filtered(
                    lambda r: r.create_date > svl_to_vacuum.create_date
                    or r.create_date == svl_to_vacuum.create_date
                    and r.id > svl_to_vacuum.id
                )
                if product.lot_valuated:
                    candidates = candidates.filtered(lambda r: r.lot_id == svl_to_vacuum.lot_id)
                if not candidates:
                    break
                qty_to_take_on_candidates = abs(svl_to_vacuum.remaining_qty)
                qty_taken_on_candidates = 0
                tmp_value = 0
                for candidate in candidates:
                    qty_taken_on_candidate = min(candidate.remaining_qty, qty_to_take_on_candidates)
                    qty_taken_on_candidates += qty_taken_on_candidate

                    candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
                    value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                    value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                    new_remaining_value = candidate.remaining_value - value_taken_on_candidate

                    candidate_vals = {
                        'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                        'remaining_value': new_remaining_value
                    }
                    candidate.write(candidate_vals)
                    if not (candidate.remaining_qty > 0):
                        all_candidates -= candidate

                    qty_to_take_on_candidates -= qty_taken_on_candidate
                    tmp_value += value_taken_on_candidate
                    if float_is_zero(qty_to_take_on_candidates, precision_rounding=product.uom_id.rounding):
                        break

                # Get the estimated value we will correct.
                remaining_value_before_vacuum = svl_to_vacuum.unit_cost * qty_taken_on_candidates
                new_remaining_qty = svl_to_vacuum.remaining_qty + qty_taken_on_candidates
                corrected_value = remaining_value_before_vacuum - tmp_value
                svl_to_vacuum.write({
                    'remaining_qty': new_remaining_qty,
                })

                # Don't create a layer or an accounting entry if the corrected value is zero.
                if svl_to_vacuum.currency_id.is_zero(corrected_value):
                    continue

                corrected_value = svl_to_vacuum.currency_id.round(corrected_value)

                move = svl_to_vacuum.stock_move_id
                new_svl_vals = new_svl_vals_real_time if product.valuation == 'real_time' else new_svl_vals_manual
                new_svl_vals.append({
                    'product_id': product.id,
                    'value': corrected_value,
                    'unit_cost': 0,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'stock_move_id': move.id,
                    'company_id': move.company_id.id,
                    'description': 'Revaluation of %s (negative inventory)' % (move.picking_id.name or move.name),
                    'stock_valuation_layer_id': svl_to_vacuum.id,
                    'lot_id': svl_to_vacuum.lot_id.id,
                })
                lot_to_update.append(svl_to_vacuum.lot_id)
                if product.valuation == 'real_time':
                    current_real_time_svls |= svl_to_vacuum
            real_time_svls_to_vacuum |= current_real_time_svls
        ValuationLayer.create(new_svl_vals_manual)
        vacuum_svls = ValuationLayer.create(new_svl_vals_real_time)

        # If some negative stock were fixed, we need to recompute the standard price.
        for product in self:
            product = product.with_company(company.id)
            if not svls_to_vacuum_by_product[product.id]:
                continue
            if product.cost_method not in ['average', 'fifo'] or float_is_zero(product.quantity_svl,
                                                                      precision_rounding=product.uom_id.rounding):
                continue
            if product.lot_valuated:
                for lot in lot_to_update:
                    if float_is_zero(lot.quantity_svl, precision_rounding=product.uom_id.rounding):
                        continue
                    lot.sudo().with_context(disable_auto_svl=True).write(
                        {'standard_price': lot.value_svl / lot.quantity_svl}
                    )
            product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl})

        vacuum_svls._validate_accounting_entries()
        self._create_fifo_vacuum_anglo_saxon_expense_entries(zip(vacuum_svls, real_time_svls_to_vacuum))

    @api.model
    def _create_fifo_vacuum_anglo_saxon_expense_entries(self, vacuum_pairs):
        """ Batch version of _create_fifo_vacuum_anglo_saxon_expense_entry
        """
        AccountMove = self.env['account.move'].sudo()
        account_move_vals = []
        vacuum_pairs_to_reconcile = []
        svls_accounts = {}
        for vacuum_svl, svl_to_vacuum in vacuum_pairs:
            if not vacuum_svl.company_id.anglo_saxon_accounting or not svl_to_vacuum.stock_move_id._is_out():
                continue
            account_move_lines = svl_to_vacuum.account_move_id.line_ids
            # Find related customer invoice where product is delivered while you don't have units in stock anymore
            reconciled_line_ids = list(set(account_move_lines._reconciled_lines()) - set(account_move_lines.ids))
            account_move = AccountMove.search([('line_ids', 'in', reconciled_line_ids)], limit=1)
            # If delivered quantity is not invoiced then no need to create this entry
            if not account_move:
                continue
            accounts = svl_to_vacuum.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=account_move.fiscal_position_id)
            if not accounts.get('stock_output') or not accounts.get('expense'):
                continue
            svls_accounts[svl_to_vacuum.id] = accounts
            description = "Expenses %s" % (vacuum_svl.description)
            move_lines = vacuum_svl.stock_move_id._prepare_account_move_line(
            vacuum_svl.quantity, vacuum_svl.value * -1,
            accounts['stock_output'].id, accounts['expense'].id,
            vacuum_svl.id, description)
            account_move_vals.append({
                'journal_id': accounts['stock_journal'].id,
                'line_ids': move_lines,
                'date': self._context.get('force_period_date', fields.Date.context_today(self)),
                'ref': description,
                'stock_move_id': vacuum_svl.stock_move_id.id,
                'move_type': 'entry',
>>>>>>> 27fa43467d14f6d4aa0bcfe5b135b3c5a429df18
            })
        return

    def _get_remaining_moves(self):
        moves_qty_by_product = {}
        for product in self:
            moves, remaining_qty = product._run_fifo_get_stack()
            moves = self.env['stock.move'].concat(*moves)
            if not moves:
                continue
            qty_by_move = {m: m.quantity for m in moves[1:]}
            qty_by_move[moves[0]] = remaining_qty
            moves_qty_by_product[product] = qty_by_move
        return moves_qty_by_product

    def _get_cogs_value(self, quantity):
        if self.cost_method in ['standard', 'average']:
            return self.standard_price * quantity
        return self._run_fifo(quantity)

    def _run_avco(self, at_date=None, lot=None, method="realtime"):
        """ Recompute the average cost of the product base on the last closing
        inventory value and all the incoming moves during the period."""
        # TODO remove at the end and do at real time
        self.ensure_one()
        # Get value and quantity from last closing
        quantity = 0
        # Get value and quantity for all incoming
        moves_domain = Domain([
            ('product_id', '=', self.id),
        ])
        if lot:
            moves_domain &= Domain([
                ('move_line_ids.lot_id', 'in', lot.id),
            ])
        if at_date:
            moves_domain &= Domain([
                ('date', '<=', at_date),
            ])
        moves_in = self.env['stock.move'].search(moves_domain & Domain(['|', ('is_in', '=', True), ('is_dropship', '=', True)]))
        moves_out = self.env['stock.move'].search(moves_domain & Domain(['|', ('is_out', '=', True), ('is_dropship', '=', True)])) if method == "realtime" else self.env['stock.move']
        # TODO convert to company UoM
        product_value_domain = Domain([('product_id', '=', self.id)])
        if lot:
            product_value_domain &= Domain(['|', ('lot_id', '=', lot.id), ('lot_id', '=', False)])
        else:
            product_value_domain &= Domain([('lot_id', '=', False)])
        if at_date:
            product_value_domain &= Domain([('date', '<=', at_date)])

        product_values = self.env['product.value'].search(product_value_domain, order="date, id")
        avco_value = 0
        avco_total_value = 0
        moves = moves_in | moves_out
        moves = moves.sorted('date, id')

        # If the last value was defined by the user just return it
        if product_values and moves_in and product_values[-1].date > moves_in[-1].date:
            quantity = self.with_context(to_date=at_date).qty_available
            if lot:
                quantity = lot.product_qty
            avco_value = product_values[-1].value
            return avco_value, avco_value * quantity

        for move in moves:
            if product_values and move.date > product_values[0].date:
                product_value = product_values[0]
                product_values = product_values[1:]
                avco_value = product_value.value
                avco_total_value = avco_value * quantity
            if move.is_in or move.is_dropship:
                in_qty = move._get_valued_qty()
                in_value = move.value
                if at_date or move.is_dropship:
                    in_value = move._get_value(at_date=at_date)
                if lot:
                    total_qty = move._get_valued_qty(lot)
                    in_value = in_value * in_qty / total_qty
                if quantity < 0 and quantity + in_qty >= 0:
                    positive_qty = quantity + in_qty
                    ratio = positive_qty / in_qty
                    avco_total_value = ratio * in_value
                else:
                    avco_total_value += in_value
                quantity += in_qty
                avco_value = avco_total_value / quantity if quantity else 0
            if move.is_out or move.is_dropship:
                out_qty = move._get_valued_qty()
                avco_total_value -= out_qty * avco_value
                quantity -= out_qty

        return avco_value, avco_total_value

    def _run_fifo_get_stack(self, lot=None, at_date=None, location=None):
        external_location = location and location.is_valued_external
        fifo_stack = []
        fifo_stack_size = 0
        if location:
            self = self.with_context(location=location.ids)  # noqa: PLW0642
        if lot:
            fifo_stack_size = lot.product_qty
        else:
            fifo_stack_size = int(self.with_context(to_date=at_date).qty_available)
        if fifo_stack_size <= 0:
            return fifo_stack, 0

        moves_domain = Domain([
            ('product_id', '=', self.id),
        ])
        if lot:
            moves_domain &= Domain([('move_line_ids.lot_id', 'in', lot.id)])
        if at_date:
            moves_domain &= Domain([('date', '<=', at_date)])
        if location:
            moves_domain &= Domain([('location_dest_id', '=', location.id)])
        if external_location:
            moves_domain &= Domain([('is_out', '=', True)])
        else:
            moves_domain &= Domain([('is_in', '=', True)])

        moves_in = self.env['stock.move'].search(moves_domain, order='date desc, id desc', limit=fifo_stack_size * 10)
        # TODO: fetch more if 10 times quantity is not enough

        remaining_qty_on_first_stack_move = 0
        # Go to the bottom of the stack
        while fifo_stack_size > 0 and moves_in:
            move = moves_in[0]
            moves_in = moves_in[1:]
            in_qty = move._get_valued_qty()
            fifo_stack.append(move)
            remaining_qty_on_first_stack_move = min(in_qty, fifo_stack_size)
            fifo_stack_size -= in_qty
        fifo_stack.reverse()
        return fifo_stack, remaining_qty_on_first_stack_move

    def _run_fifo(self, quantity, lot=None, at_date=None, location=None):
        """ Returns the value for the next outgoing product base on the qty give as argument."""
        self.ensure_one()
        external_location = location and location.is_valued_external

        fifo_cost = 0
        fifo_stack, qty_on_first_move = self._run_fifo_get_stack(lot=lot, at_date=at_date, location=location)
        # Going up to get the quantity in the argument
        while quantity > 0 and fifo_stack:
            move = fifo_stack.pop(0)
            if qty_on_first_move:
                valued_qty = move._get_valued_qty()
                in_qty = qty_on_first_move
                in_value = move.value * in_qty / valued_qty
                qty_on_first_move = 0
            else:
                in_qty = move._get_valued_qty()
                in_value = move.value
            if at_date and not external_location:
                in_value = move._get_value(at_date=at_date)
            if in_qty > quantity:
                in_value = in_value * quantity / in_qty
                in_qty = quantity
            fifo_cost += in_value
            quantity -= in_qty
        return fifo_cost

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        # TODO: Add extra value and extra quantity kwargs to avoid total recomputation
        for product in self:
            if product.cost_method == 'standard':
                continue
            product.with_context(disable_auto_revaluation=True).standard_price = product._run_avco()[0]


class ProductCategory(models.Model):
    _inherit = 'product.category'

    anglo_saxon_accounting = fields.Boolean(
        string="Use Anglo-Saxon Accounting", compute="_compute_anglo_saxon_accounting",
        help="If checked, the product will be valued using the Anglo-Saxon accounting method.")
    property_valuation = fields.Selection(
        string="Inventory Valuation",
        selection=[
            ('periodic', 'Periodic (at closing)'),
            ('real_time', 'Perpetual (at invoicing)'),
        ],
        company_dependent=True, copy=True, tracking=True,
        help="""Manual: The accounting entries to value the inventory are not posted automatically.
        Automated: An accounting entry is automatically created to value the inventory when a product enters or leaves the company.
        """)
    property_cost_method = fields.Selection(
        string="Costing Method",
        selection=[
            ('standard', "Standard Price"),
            ('fifo', "First In First Out (FIFO)"),
            ('average', "Average Cost (AVCO)"),
        ],
        company_dependent=True, copy=True,
        default=lambda self: self.env.company.cost_method,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
        Average Cost (AVCO): The products are valued at weighted average cost.
        First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.
        """,
        tracking=True,
    )
    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal', company_dependent=True,
        help="When doing automated inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed.")
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""When automated inventory valuation is enabled on a product, this account will hold the current value of the products.""")
    property_price_difference_account_id = fields.Many2one(
        'account.account', 'Price Difference Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""With perpetual valuation, this account will hold the price difference between the standard price and the bill price.""")

    @api.depends_context('company')
    def _compute_anglo_saxon_accounting(self):
        self.anglo_saxon_accounting = self.env.company.anglo_saxon_accounting
