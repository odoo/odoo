# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, time, timedelta
from collections import defaultdict
from typing import NamedTuple

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL, split_every


class FifoCandidate(NamedTuple):
    quantity: float
    value: float
    out_move: models.Model = None


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cost_method = fields.Selection(
        selection_add=[('fifo', "First In First Out (FIFO)")],
    )
    lot_valuated = fields.Boolean(
        string="Valuation by Lot/Serial",
        compute='_compute_lot_valuated', store=True, readonly=False,
        help="If checked, the valuation will be specific by Lot/Serial number.",
    )

    @api.depends('tracking', 'is_storable')
    def _compute_lot_valuated(self):
        for product in self:
            if product.tracking not in ['lot', 'serial']:
                product.lot_valuated = False

    def write(self, vals):
        product_ids_to_update = set()
        lot_ids_to_update = set()
        if 'categ_id' in vals:
            category = self.env['product.category'].browse(vals['categ_id'])
            cost_method = category.property_cost_method if category else self.env.company.cost_method
            for product in self:
                if product.cost_method != cost_method:
                    product_ids_to_update.update(product.product_variant_ids.ids)

        if 'lot_valuated' in vals:
            if vals.get('lot_valuated'):
                products_to_enable = self.filtered(lambda p: not p.lot_valuated)
                if products_to_enable:
                    problematic_quants = self.env['stock.quant'].search([
                        ('product_id', 'in', products_to_enable.product_variant_ids.ids),
                        ('lot_id', '=', False),
                        ('quantity', '!=', 0),
                        ('location_id.is_valued', '=', True),
                    ])
                    if problematic_quants:
                        raise UserError(self.env._(
                            "You cannot enable lot valuation because the following products have"
                            " on-hand quantities without a lot/serial number:\n%s",
                            problematic_quants.product_id.mapped('display_name'),
                        ))
            for product in self:
                if product.lot_valuated != vals.get('lot_valuated', product.lot_valuated):
                    product_ids_to_update.update(product.product_variant_ids.ids)

        products_to_update = self.env['product.product'].browse(product_ids_to_update)
        lot_ids_to_update.update(self.env['stock.lot'].sudo().search([
            ('product_id', 'in', products_to_update.filtered(lambda p: p.lot_valuated).ids),
        ]).ids)

        res = super().write(vals)
        if 'lot_valuated' in vals:
            lot_ids_to_update.update(self.env['stock.lot'].sudo().search([
                ('product_id', 'in', self.product_variant_ids.ids),
            ]).ids)
        if product_ids_to_update:
            self.env['product.product'].browse(product_ids_to_update)._update_standard_price()
        if lot_ids_to_update:
            self.env['stock.lot'].browse(lot_ids_to_update).sudo()._update_standard_price()
        return res


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

    @api.depends_context('to_date', 'company', 'warehouse_id')
    @api.depends('cost_method', 'stock_move_ids.value', 'standard_price')
    def _compute_value(self):
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        # PERF: Pre-compute:the sum of 'total_value' of lots per product in go
        std_price_by_company_id = {}
        total_value_by_company_id = {}
        lot_valuated_products_ids = {p.id for p in self if p.lot_valuated}

        at_date = self.env.context.get('to_date')
        original_value = at_date
        at_date = fields.Datetime.to_datetime(at_date)
        if (isinstance(original_value, date) and not isinstance(original_value, datetime)) or \
            (isinstance(original_value, str) and len(original_value) == 10):
            at_date = datetime.combine(at_date.date(), time.max)

        for company in self.env.companies:
            std_price_by_product_id = defaultdict(float)
            total_value_by_product_id = defaultdict(float)

            products = self.with_company(company.id).with_context(allowed_company_ids=company.ids)
            products = products._with_valuation_context()
            if at_date:
                products = products.with_context(at_date=at_date, to_date=at_date)

            env = products.env

            if lot_valuated_products_ids:
                domain = Domain([('product_id', 'in', lot_valuated_products_ids)])
                if not at_date and not self.env.context.get('warehouse_id'):
                    domain &= Domain([('product_qty', '!=', 0)])
                lots_by_product = env['stock.lot']._read_group(
                    domain,
                    groupby=['product_id'],
                    aggregates=['id:recordset']
                )
                # Collect all lots and trigger batch computation of total_value
                env['stock.lot'].browse(
                        lot.id
                        for _, lots in lots_by_product
                        for lot in lots
                ).mapped('total_value')
                for product, lots in lots_by_product:
                    value = sum(lots.mapped('total_value'))
                    std_price_by_product_id[product.id] = value / product.qty_available if product.qty_available else product.standard_price
                    total_value_by_product_id[product.id] = value

            product_ids_grouped_by_cost_method = defaultdict(set)
            ratio_by_product_id = {}
            for product in products:
                if product.lot_valuated:
                    continue
                product_whole_company_context = product
                if 'warehouse_id' in self.env.context:
                    product_whole_company_context = product.with_context(warehouse_id=False)
                if product.uom_id.is_zero(product.qty_available):
                    total_value_by_product_id[product.id] = 0
                    std_price_by_product_id[product.id] = product.standard_price
                    continue
                if product.uom_id.is_zero(product_whole_company_context.qty_available):
                    total_value_by_product_id[product.id] = product.standard_price * product.qty_available
                    std_price_by_product_id[product.id] = product.standard_price
                    continue
                if product.uom_id.compare(product.qty_available, product_whole_company_context.qty_available) != 0:
                    ratio = product.qty_available / product_whole_company_context.qty_available
                    ratio_by_product_id[product.id] = ratio

                product_ids_grouped_by_cost_method[product.cost_method].add(product.id)

            for cost_method, product_ids in product_ids_grouped_by_cost_method.items():
                products = products.env['product.product'].browse(product_ids).with_context(warehouse_id=False)
                # To remove once price_unit isn't truncate in sql anymore (no need of force_recompute)
                if cost_method == 'standard':
                    std_prices, total_values = products._run_standard(at_date=at_date)
                elif cost_method == 'average':
                    std_prices, total_values = products._run_avco(at_date=at_date)
                else:
                    std_prices, total_values = products._run_fifo(at_date=at_date)

                std_price_by_product_id.update(std_prices)
                total_value_by_product_id.update(total_values)

            for product in products:
                total_value = total_value_by_product_id.get(product.id, 0)
                total_value_by_product_id[product.id] = total_value * ratio_by_product_id.get(product.id, 1)

            std_price_by_company_id[company.id] = std_price_by_product_id
            total_value_by_company_id[company.id] = total_value_by_product_id

        for product in self:
            product.total_value = sum(c.currency_id._convert(total_value_by_company_id[c.id].get(product.id, 0), self.env.company.currency_id) for c in self.env.companies)
            product.avg_cost = product.total_value / product._with_valuation_context().qty_available if product._with_valuation_context().qty_available else std_price_by_company_id[self.env.company.id].get(product.id, product.standard_price)

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products._change_standard_price({product: 0 for product in products if product.standard_price}, valuation_date=datetime.min)
        return products

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

    def _change_standard_price(self, old_price, valuation_date=None):
        product_values = []
        product_ids_lot_valuated = set()
        date = valuation_date or fields.Datetime.now()
        for product in self:
            if product.cost_method == 'fifo' or product.standard_price == old_price.get(product):
                continue

            if product.lot_valuated:
                product_ids_lot_valuated.add(product.id)

            product_values.append({
                'product_id': product.id,
                'value': product.standard_price,
                'company_id': product.company_id.id or self.env.company.id,
                'date': date,
                'description': _('Price update from %(old_price)s to %(new_price)s by %(user)s',
                    old_price=old_price.get(product), new_price=product.standard_price, user=self.env.user.name)
            })
        self.env['product.value'].sudo().create(product_values)
        if product_ids_lot_valuated:
            for (product, lots) in self.env['stock.lot']._read_group(
                    [('product_id', 'in', product_ids_lot_valuated)], ['product_id'], ['id:recordset']):
                lots.with_context(disable_auto_revaluation=True).standard_price = product.standard_price
        return

    def _correct_inventory_valuation(self, from_date):
        def replay(products, cost_method, lot=False):
            if cost_method == 'standard':
                products._run_standard(at_date=from_date, correction=True)
            elif cost_method == 'average':
                products._run_avco(at_date=from_date, lot=lot, correction=True)
            else:
                products._run_fifo(at_date=from_date, lot=lot, correction=True)

        lot_valuated = self.filtered(lambda p: p.lot_valuated and p.cost_method != 'standard')
        for product in lot_valuated:
            boundary = from_date - timedelta(seconds=1) if from_date != datetime.min else from_date
            moves_in_scope = product._get_stock_moves_with_valuation_by_product(boundary).get(product, self.env['stock.move'])
            moves_in_scope.filtered('is_out').value = 0.0
            for lot in moves_in_scope.move_line_ids.lot_id:
                replay(product, product.cost_method, lot=lot)

        for cost_method, products in (self - lot_valuated).grouped('cost_method').items():
            replay(products, cost_method)

    def _get_stock_moves_with_valuation_by_product(self, from_date, lot=False):
        domain = [
            ('product_id', 'in', self.ids), ('date', '>', from_date),
            ('company_id', '=', self.env.company.id),
            '|', ('is_in', '=', True), ('is_out', '=', True),
        ]
        if lot:
            domain += [('move_line_ids.lot_id', 'in', lot.id)]
        return self.env['stock.move'].search(domain, order='product_id, date, id').grouped('product_id')

    def _get_std_price_history_by_product(self, from_date):
        return self.env['product.value'].sudo().search([
            ('product_id', 'in', self.ids), ('move_id', '=', False), ('date', '>', from_date),
            ('company_id', '=', self.env.company.id),
        ], order='product_id, date, id').grouped('product_id')

    def _get_last_product_value(self, date=None, lot=False):
        domain = Domain([
            ('product_id', 'in', self.ids),
            ('move_id', '=', False),
            ('company_id', '=', self.env.company.id),
        ])
        if lot:
            domain &= Domain(['|', ('lot_id', '=', lot.id), ('lot_id', '=', False)])
        else:
            domain &= Domain([('lot_id', '=', False)])
        if date:
            domain &= Domain([('date', '<=', date)])

        query = self.env['product.value'].sudo()._search(domain)
        query_select = SQL('distinct ON (product_value.product_id) product_value.id')
        query.order = SQL('product_value.product_id, product_value.date DESC, product_value.id DESC')
        query._ids = tuple(id_ for id_, in self.env.execute_query(query.select(query_select)))
        product_values = self.env['product.value'].browse(query._ids)
        product_values.sudo().fetch(['product_id', 'value', 'date'])
        return {pv.product_id: pv for pv in product_values}

    def _get_last_in(self, date=None):
        last_in_domain = Domain([('is_in', '=', True), ('product_id', '=', self.id)])
        if date:
            last_in_domain &= Domain([('date', '<=', date)])
        last_in = self.env['stock.move'].search(last_in_domain, order='date desc, id desc', limit=1)
        return last_in

    def _with_valuation_context(self):
        valued_locations = self.env['stock.location'].with_context(active_test=False).search([('is_valued', '=', True)])
        return self.with_context(location=valued_locations.ids, strict=True, owners=[False, self.env.company.partner_id.id])

    def _get_remaining_moves(self):
        moves_qty_by_product = {}
        for product in self:
            qty_by_move = defaultdict(float)
            lots = [None]
            if product.lot_valuated:
                lots = product.stock_quant_ids.filtered(
                    lambda q: q.lot_id and q.company_id == self.env.company and q.location_id.is_valued and q.quantity > 0
                ).lot_id or [None]
            for lot in lots:
                moves, remaining_qty = product._get_fifo_stack(lot=lot, allow_negative=True)
                if not moves:
                    continue
                sign = -1 if moves[0].is_out else 1
                qty_by_move[moves[0]] += remaining_qty
                for move in moves[1:]:
                    qty_by_move[move] += sign * move._get_valued_qty(lot)
            if not qty_by_move:
                continue
            moves_qty_by_product[product] = qty_by_move
        return moves_qty_by_product

    def _run_standard(self, at_date=None, lot=None, correction=False):
        if at_date and correction and at_date != datetime.min:
            at_date = at_date - timedelta(seconds=1)
        std_price_by_product_id = {product.id: product.standard_price for product in self}
        if at_date:
            product_value_by_product = self._get_last_product_value(at_date, lot=lot)
            std_price_by_product_id = {
                product.id: product_value_by_product[product].value if product in product_value_by_product else product.standard_price
                for product in self
            }
        value_by_product_id = {p.id: p.qty_available * std_price_by_product_id.get(p.id, 0) for p in self}
        if not correction:
            return std_price_by_product_id, value_by_product_id

        moves_by_product = self._get_stock_moves_with_valuation_by_product(at_date)
        std_price_history_by_product = self._get_std_price_history_by_product(at_date)

        for product in self:
            std_price = std_price_by_product_id.get(product.id, product.standard_price)
            price_changes = iter(std_price_history_by_product.get(product, self.env['product.value']))
            next_change = next(price_changes, None)
            for move in moves_by_product.get(product, self.env['stock.move']):
                while next_change and next_change.date <= move.date:
                    std_price = next_change.value
                    next_change = next(price_changes, None)
                if move.is_in:
                    continue
                new_value = move._get_valued_qty(signed=True) * std_price
                if move.value != new_value:
                    move.value = new_value

        return std_price_by_product_id, value_by_product_id

    def _run_avco(self, at_date=None, lot=None, force_recompute=None, correction=False):
        if at_date and correction and at_date != datetime.min:
            at_date = at_date - timedelta(seconds=1)
        std_price_by_product_id = defaultdict(float)
        value_by_product_id = defaultdict(float)
        quantity_by_product_id = {}
        date_by_product_id = {}

        if not at_date and not force_recompute:
            std_price_by_product_id = {p.id: p.standard_price for p in self}
            value_by_product_id = {p.id: p.qty_available * std_price_by_product_id.get(p.id, 0) for p in self}
            return std_price_by_product_id, value_by_product_id

        moves_domain = Domain([
            ('product_id', 'in', self._as_query()),
            ('company_id', '=', self.env.company.id),
            '|', '|', ('is_in', '=', True), ('is_dropship', '=', True), ('is_out', '=', True)
        ])
        if lot:
            moves_domain &= Domain([
                ('move_line_ids.lot_id', 'in', lot.id),
            ])
        if at_date and not correction:
            moves_domain &= Domain([
                ('date', '<=', at_date),
            ])

        last_manual_value_by_product = self._get_last_product_value(at_date, lot=lot)
        oldest_manual_value = min(pv.date for pv in last_manual_value_by_product.values()) if last_manual_value_by_product else False
        if oldest_manual_value and self.env['product.product'].concat(last_manual_value_by_product.keys()) == self:
            moves_domain &= Domain([('date', '>=', oldest_manual_value)])

        for manual_value in last_manual_value_by_product.values():
            product = manual_value.product_id
            if lot:
                quantity = lot.with_context(to_date=manual_value.date).product_qty
            else:
                quantity = product.with_context(to_date=manual_value.date).qty_available

            std_price_by_product_id[product.id] = manual_value.value
            quantity_by_product_id[product.id] = quantity
            value_by_product_id[product.id] = manual_value.value * quantity
            date_by_product_id[product.id] = manual_value.date

        self.env['product.value'].invalidate_model()  # Avoid keeping too many records in cache

        moves = self.env['stock.move'].search_fetch(
            moves_domain,
            field_names=['id'],
            order='product_id, date, id'
        )
        # PERF avoid memoryerror
        move_fields = ['date', 'is_dropship', 'is_in', 'is_out', 'location_dest_id', 'location_id', 'move_line_ids', 'picked', 'value', 'product_id']
        move_line_fields = ['company_id', 'location_id', 'location_dest_id', 'lot_id', 'owner_id', 'picked', 'quantity_product_uom']

        product, valuation_from_date = False, False
        batch_size = 50000

        move_ids_by_product = defaultdict(list)
        std_price_history_by_product_id = False
        if correction:
            std_price_history_by_product_id = self._get_std_price_history_by_product(at_date)
        # Limit the memory usage since it's possible to have millions of stock.move
        for moves_batch in split_every(batch_size, moves.ids):
            moves_batch = self.env['stock.move'].browse(moves_batch)
            moves_batch.fetch(['product_id', 'date'])

            for move in moves_batch:
                if move.product_id != product:
                    product = move.product_id
                    valuation_from_date = date_by_product_id.get(product.id)
                if valuation_from_date and move.date <= valuation_from_date:
                    continue
                move_ids_by_product[product].append(move.id)

            self.env['stock.move'].invalidate_model()

        for product, move_ids in move_ids_by_product.items():
            product_moves = self.env['stock.move'].browse(move_ids)

            first_move = product_moves[0]
            quantity = quantity_by_product_id.get(product.id, 0)
            average_cost = std_price_by_product_id.get(product.id, first_move.value / first_move._get_valued_qty() if first_move._get_valued_qty() else 0)
            value = value_by_product_id.get(product.id, 0)

            price_changes = iter(std_price_history_by_product_id.get(product, self.env['product.value']) if correction else self.env['product.value'])
            next_change = next(price_changes, None)

            for moves_batch in split_every(batch_size, product_moves.ids):
                moves_batch = self.env['stock.move'].browse(moves_batch)
                moves_batch.fetch(move_fields)
                moves_batch.move_line_ids.fetch(move_line_fields)
                for move in moves_batch:
                    while next_change and next_change.date <= move.date:
                        average_cost = next_change.value
                        value = average_cost * quantity
                        next_change = next(price_changes, None)
                    if move.is_in or move.is_dropship:
                        in_qty = move._get_valued_qty()
                        in_value = move.value
                        if move.is_dropship:
                            in_value = move.sudo()._get_value(forced_std_price=average_cost)
                        if lot:
                            lot_qty = move._get_valued_qty(lot)
                            in_value = (in_value * lot_qty / in_qty) if in_qty else 0
                            in_qty = lot_qty
                        previous_qty = quantity
                        quantity += in_qty
                        if previous_qty > 0:
                            value += in_value
                            average_cost = value / quantity
                        elif previous_qty <= 0:
                            average_cost = in_value / in_qty if in_qty else average_cost
                            value = average_cost * quantity
                    if move.is_out or move.is_dropship:
                        out_qty = move._get_valued_qty()
                        out_value = out_qty * average_cost
                        if lot:
                            lot_qty = move._get_valued_qty(lot)
                            out_value = (out_value * lot_qty / out_qty) if out_qty else 0
                            out_qty = lot_qty
                        if correction and move.date > at_date and move.is_out:
                            if lot:
                                move.value -= out_value
                            elif move.value != -out_value:
                                move.value = -out_value
                        value -= out_value
                        quantity -= out_qty

                self.env['stock.move'].invalidate_model()  # Avoid keeping too many records in cache
                self.env['stock.move.line'].invalidate_model()

            std_price_by_product_id[product.id] = average_cost
            value_by_product_id[product.id] = value

        return std_price_by_product_id, value_by_product_id

    def _run_fifo(self, at_date=None, lot=None, correction=False):
        std_price_by_product_id = {}
        value_by_product_id = {}
        stack_by_product = defaultdict(list)
        products = self.sudo()._with_valuation_context()
        if at_date:
            if correction and at_date != datetime.min:
                at_date = at_date - timedelta(seconds=1)
            products = products.with_context(to_date=at_date)
            if lot:
                lot = lot.with_context(to_date=at_date)
        qty_by_product = {p: (lot.product_qty if lot else p.qty_available) for p in products}
        for product in products:
            quantity = qty_by_product.get(product, 0)
            std_price = lot.standard_price if lot else product.standard_price
            if product.uom_id.compare(quantity, 0) < 0:
                if at_date:
                    last_in = product._get_last_in(at_date)
                    std_price = last_in._get_price_unit() if last_in else std_price
                std_price_by_product_id[product.id] = std_price
                value_by_product_id[product.id] = quantity * std_price
                if correction:
                    stack_by_product[product] = [FifoCandidate(quantity, quantity * std_price)]
                continue

            fifo_stack, qty_on_first_move = product._get_fifo_stack(lot=lot, at_date=at_date)
            value = 0
            for index, move in enumerate(fifo_stack):
                if index == 0 and qty_on_first_move:
                    full_qty = move._get_valued_qty()
                    valued_qty = qty_on_first_move
                    valued_value = move.value * qty_on_first_move / full_qty if full_qty else 0
                else:
                    valued_qty = move._get_valued_qty(lot=lot)
                    valued_value = move.value
                    if lot:
                        full_qty = move._get_valued_qty()
                        valued_value = move.value * valued_qty / full_qty if full_qty else 0
                value += valued_value
                if correction:
                    stack_by_product[product].append(FifoCandidate(valued_qty, valued_value))

            std_price = value / quantity if quantity else std_price
            std_price_by_product_id[product.id] = std_price
            value_by_product_id[product.id] = value

        if not correction:
            return std_price_by_product_id, value_by_product_id

        moves_by_product = self._get_stock_moves_with_valuation_by_product(at_date, lot=lot)
        std_price_history_by_product = self._get_std_price_history_by_product(at_date)

        for product in self:
            stack = stack_by_product[product]
            unit_price = std_price_by_product_id.get(product.id, product.standard_price)
            price_changes = iter(std_price_history_by_product.get(product, self.env['product.value']))
            next_change = next(price_changes, None)
            for move in moves_by_product.get(product, self.env['stock.move']):
                while next_change and next_change.date <= move.date:
                    unit_price = next_change.value
                    stack[:] = [FifoCandidate(m.quantity, m.quantity * unit_price, m.out_move) for m in stack]
                    next_change = next(price_changes, None)

                if move.is_in:
                    full_in_qty = move._get_valued_qty()
                    in_qty = move._get_valued_qty(lot=lot) if lot else full_in_qty
                    unit_price = move.value / full_in_qty if full_in_qty else unit_price
                    while in_qty > 0 and stack and stack[0].quantity < 0:
                        shortage_move = stack[0]
                        shortage = -shortage_move.quantity
                        filled = min(shortage, in_qty)
                        if shortage_move.out_move:
                            old_unit = shortage_move.value / shortage_move.quantity
                            shortage_move.out_move.value += filled * (old_unit - unit_price)
                        in_qty -= filled
                        remaining_qty = shortage_move.quantity + filled
                        if remaining_qty < 0:
                            stack[0] = FifoCandidate(remaining_qty, remaining_qty * unit_price, shortage_move.out_move)
                        else:
                            stack.pop(0)
                    if in_qty > 0:
                        stack.append(FifoCandidate(in_qty, in_qty * unit_price))
                elif move.is_out:
                    out_qty = move._get_valued_qty(lot=lot) if lot else move._get_valued_qty()
                    out_value = 0
                    while out_qty > 0 and stack and stack[0].quantity > 0:
                        candidate_qty, candidate_value = stack[0].quantity, stack[0].value
                        if candidate_qty > out_qty:
                            consumed_value = candidate_value * out_qty / candidate_qty
                            stack[0] = FifoCandidate(candidate_qty - out_qty, candidate_value - consumed_value)
                            out_value += consumed_value
                            out_qty = 0
                        else:
                            out_value += candidate_value
                            out_qty -= candidate_qty
                            stack.pop(0)
                    if out_qty > 0:
                        out_value += out_qty * unit_price
                        stack.append(FifoCandidate(-out_qty, -out_qty * unit_price, move))
                    if lot:
                        move.value -= out_value
                    elif move.value != -out_value:
                        move.value = -out_value

            std_price_by_product_id[product.id] = unit_price
            value_by_product_id[product.id] = sum(stack_tuple.value for stack_tuple in stack)

        return std_price_by_product_id, value_by_product_id

    def _get_fifo_value(self, quantity, lot=None, stack_size_extra_qty=0):
        """ Returns the value for the next outgoing product base on the qty give as argument."""
        self.ensure_one()
        if self.uom_id.compare(quantity, 0) <= 0:
            std_price = lot.standard_price if lot else self.standard_price
            return quantity * std_price

        fifo_cost = 0
        fifo_stack, qty_on_first_move = self._get_fifo_stack(lot=lot, stack_size_extra_qty=stack_size_extra_qty)
        last_move = False
        # Going up to get the quantity in the argument
        while quantity > 0 and fifo_stack:
            move = fifo_stack.pop(0)
            last_move = move
            move_value = move.value
            if qty_on_first_move:
                valued_qty = move._get_valued_qty()
                in_qty = qty_on_first_move
                in_value = move_value * in_qty / valued_qty
                qty_on_first_move = 0
            else:
                in_qty = move._get_valued_qty(lot=lot)
                in_value = move_value
                if lot:
                    valued_qty = move._get_valued_qty()
                    in_value = in_value * in_qty / valued_qty if valued_qty else 0
            if in_qty > quantity:
                in_value = in_value * quantity / in_qty
                in_qty = quantity
            fifo_cost += in_value
            quantity -= in_qty
        # When we required more quantity than available we extrapolate with the last known price
        if quantity > 0:
            if last_move and last_move.quantity:
                fifo_cost += quantity * (last_move.value / last_move.quantity)
            else:
                fifo_cost += quantity * self.standard_price
        return fifo_cost

    def _get_fifo_stack(self, lot=None, at_date=None, allow_negative=False, stack_size_extra_qty=0):
        """ :param allow_negative: when the on hand is negative (oversold), build a stack of
            the outgoing moves that make up that shortage instead of returning an empty
            one. Only the re-costing/replay paths want this; a plain consumption does not,
            as it has nothing on hand to consume and extrapolates the price instead.
        :param stack_size_extra_qty: quantity to add to the on-hand stack size, for when
            ``qty_available`` no longer reflects the valuation moment (e.g. out moves
            valued once done, or several moves validated together).
        """
        fifo_stack = []
        fifo_stack_size = 0
        if lot:
            fifo_stack_size = lot.product_qty
        else:
            fifo_stack_size = self._with_valuation_context().with_context(to_date=at_date).qty_available
        fifo_stack_size += stack_size_extra_qty
        if self.uom_id.is_zero(fifo_stack_size):
            return fifo_stack, 0

        # A positive on hand is covered by incoming moves; a negative one (oversold) is
        # made of the outgoing moves whose delivered quantity was not in stock. In the
        # latter case the stack holds those out moves and their remaining quantity is
        # negative, so a later incoming move can find them and re-cost them.
        oversold = self.uom_id.compare(fifo_stack_size, 0) < 0
        if oversold and not allow_negative:
            # Nothing on hand to consume; leave the stack empty so the caller extrapolates.
            return fifo_stack, 0
        sign = -1 if oversold else 1
        remaining_size = abs(fifo_stack_size)

        moves_domain = Domain([
            ('product_id', '=', self.id),
            ('company_id', 'in', self.env.companies.ids),
        ])
        if lot:
            moves_domain &= Domain([('move_line_ids.lot_id', 'in', lot.id)])
        if at_date:
            moves_domain &= Domain([('date', '<=', at_date)])
        moves_domain &= Domain([('is_out' if oversold else 'is_in', '=', True)])

        # Arbitrary limit as we can't guess how many moves correspond to the qty_available, but avoid fetching all moves at the same time.
        initial_limit = 100
        moves = self.env['stock.move'].search(moves_domain, order='date desc, id desc', limit=initial_limit)

        remaining_qty_on_first_stack_move = 0
        current_offset = 0
        # Go to the bottom of the stack
        while self.uom_id.compare(remaining_size, 0) > 0 and moves:
            move = moves[0]
            moves = moves[1:]
            move_qty = move._get_valued_qty(lot=lot)
            fifo_stack.append(move)
            remaining_qty_on_first_stack_move = sign * min(move_qty, remaining_size)
            remaining_size -= move_qty
            if self.uom_id.compare(remaining_size, 0) > 0 and not moves:
                # We need to fetch more moves
                current_offset += 1
                moves = self.env['stock.move'].search(moves_domain, order='date desc, id desc', offset=current_offset * initial_limit, limit=initial_limit)
        fifo_stack.reverse()
        return fifo_stack, remaining_qty_on_first_stack_move

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        if extra_value is not None or extra_quantity is not None:
            super()._update_standard_price(extra_value=extra_value, extra_quantity=extra_quantity)
        products_by_cost_method = defaultdict(set)
        self_ctx = self.with_context(disable_auto_revaluation=True, mail_notrack=True)
        for product in self_ctx:
            if product.lot_valuated and product.cost_method != 'standard':
                product.sudo().standard_price = product.avg_cost
                continue
            products_by_cost_method[product.cost_method].add(product.id)
        for cost_method, product_ids in products_by_cost_method.items():
            products = self_ctx.env['product.product'].browse(product_ids)
            if cost_method == 'standard':
                continue
            if cost_method == 'fifo':
                for product in products:
                    qty_available = product._with_valuation_context().qty_available
                    if product.uom_id.compare(qty_available, 0) > 0:
                        product.sudo().standard_price = product.total_value / qty_available
                    elif last_in := product._get_last_in():
                        if last_in_price_unit := last_in._get_price_unit():
                            product.sudo().standard_price = last_in_price_unit
                continue
            if cost_method == 'average':
                new_standard_price_by_product = self._run_avco(force_recompute=True)[0]
                for product in products:
                    if product.id in new_standard_price_by_product:
                        product.sudo().standard_price = new_standard_price_by_product[product.id]


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_cost_method = fields.Selection(
        selection_add=[('fifo', "First In First Out (FIFO)")],
        ondelete={'fifo': 'set default'},
    )
    anglo_saxon_accounting = fields.Boolean(
        string="Use Anglo-Saxon Accounting", compute="_compute_anglo_saxon_accounting",
        help="If checked, the product will be valued using the Anglo-Saxon accounting method.")

    @api.depends_context('company')
    def _compute_anglo_saxon_accounting(self):
        self.anglo_saxon_accounting = self.env.company.anglo_saxon_accounting

    def write(self, vals):
        products_to_update = self.env['product.product']
        if 'property_cost_method' in vals:
            updated_categories = self.filtered(lambda c: c.property_cost_method != vals['property_cost_method'])
            if updated_categories:
                products_to_update = self.env['product.product'].search([('categ_id', 'in', updated_categories.ids)])
        res = super().write(vals)
        if products_to_update:
            products_to_update._correct_inventory_valuation(self.env.company._get_last_closing_date())
            products_to_update._update_standard_price()
        products_lot_valuated = products_to_update.filtered(lambda p: p.lot_valuated)
        if products_lot_valuated:
            self.env['stock.lot'].sudo().search([('product_id', 'in', products_lot_valuated.ids)])._update_standard_price()
        return res
