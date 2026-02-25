# Part of Odoo. See LICENSE file for full copyright and licensing details.
from bisect import bisect
from collections import defaultdict
from datetime import date, datetime, time

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL, split_every


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
        compute='_compute_valuation', search='_search_valuation',
    )
    lot_valuated = fields.Boolean(
        string="Valuation by Lot/Serial",
        compute='_compute_lot_valuated', store=True, readonly=False,
        help="If checked, the valuation will be specific by Lot/Serial number.",
    )
    # TODO remove in master
    property_price_difference_account_id = fields.Many2one(
        'account.account', 'Price Difference Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""With perpetual valuation, this account will hold the price difference between the standard price and the bill price.""")

    def _search_valuation(self, operator, value):
        if operator != '=':
            raise UserError(self.env._("You can only use the '=' operator to search on valuation field."))
        if value not in ['periodic', 'real_time']:
            raise UserError(self.env._("Only the value 'periodic' and 'real_time' are accepted to search on valuation field."))
        domain_categ = Domain([('categ_id.property_valuation', operator, value)])
        domain_company = Domain(['|', ('categ_id.property_valuation', '=', False), ('categ_id', '=', False), ('company_id.inventory_valuation', operator, value)])

        if self.env.company.inventory_valuation and self.env.company.inventory_valuation == value:
            domain_company = Domain(['|', ('categ_id.property_valuation', '=', False), ('categ_id', '=', False), '|', ('company_id.inventory_valuation', operator, value), ('company_id', '=', False)])
        return domain_company | domain_categ

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
        for product_template in self:
            product_template.valuation = product_template.categ_id.with_company(
                product_template.company_id).property_valuation or self.env.company.inventory_valuation

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
                        ('location_id.is_valued_internal', '=', True),
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

    # -------------------------------------------------------------------------
    # Misc.
    # -------------------------------------------------------------------------
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super()._get_product_accounts()

        accounts['stock_valuation'] = (
                self.categ_id.property_stock_valuation_account_id
                or self.categ_id._fields['property_stock_valuation_account_id'].get_company_dependent_fallback(self.categ_id)
                or self.env.company.account_stock_valuation_id
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
                or self.env.company.account_stock_journal_id
            )
        })
        return accounts

    def _get_price_diff_account(self):
        price_diff_account = super()._get_price_diff_account()
        if self.cost_method == 'standard':
            price_diff_account = self.categ_id.property_price_difference_account_id
        return price_diff_account


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
        products = self._with_valuation_context()

        at_date = self.env.context.get('to_date')
        original_value = at_date
        at_date = fields.Datetime.to_datetime(at_date)
        if (isinstance(original_value, date) and not isinstance(original_value, datetime)) or \
            (isinstance(original_value, str) and len(original_value) == 10):
            at_date = datetime.combine(at_date.date(), time.max)

        if at_date:
            products = products.with_context(at_date=at_date, to_date=at_date)

        # PERF: Pre-compute:the sum of 'total_value' of lots per product in go
        std_price_by_company_id = {}
        total_value_by_company_id = {}
        lot_valuated_products_ids = {p.id for p in self if p.lot_valuated}
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
                if not self.env.context.get('warehouse_id'):
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
                    std_prices, total_values = products._run_standard_batch(at_date=at_date)
                elif cost_method == 'average':
                    std_prices, total_values = products._run_average_batch(at_date=at_date)
                else:
                    std_prices, total_values = products._run_fifo_batch(at_date=at_date)

                std_price_by_product_id.update(std_prices)
                total_value_by_product_id.update(total_values)

            for product in products:
                total_value = total_value_by_product_id.get(product.id, 0)
                total_value_by_product_id[product.id] = total_value * ratio_by_product_id.get(product.id, 1)

            std_price_by_company_id[company.id] = std_price_by_product_id
            total_value_by_company_id[company.id] = total_value_by_product_id

        for product in self:
            product.total_value = sum(total_value_by_company_id[c.id].get(product.id, 0) for c in self.env.companies)
            product.avg_cost = product.total_value / product.qty_available if product.qty_available else std_price_by_company_id[self.env.company.id].get(product.id, product.standard_price)

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products.with_context(valuation_date=datetime.min)._change_standard_price({product: 0 for product in products if product.standard_price})
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

    def _change_standard_price(self, old_price):
        product_values = []
        product_ids_lot_valuated = set()
        date = self.env.context.get('valuation_date') or fields.Datetime.now()
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

    def _get_standard_price_at_date(self, date=None):
        """ Get Last Price History """
        self.ensure_one()
        if not date or date == fields.Date.today():
            return self.standard_price
        if self.cost_method != 'standard':
            raise ValidationError(_("You can only get the standard price at a given date for products with 'Standard Price' as cost method."))
        product_value = self._get_last_product_value(date).get(self)
        return product_value.value if product_value else self.standard_price

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
        valued_locations = self.env['stock.location'].search([('is_valued_internal', '=', True)])
        return self.with_context(location=valued_locations.ids, owners=[False, self.env.company.partner_id.id], strict=True)

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

    def _run_standard_batch(self, at_date=None, lot=None):
        std_price_by_product_id = {product.id: product.standard_price for product in self}
        if at_date:
            product_value_by_product = self._get_last_product_value(at_date, lot=lot)
            std_price_by_product_id = {
                product.id: product_value_by_product[product].value if product in product_value_by_product else product.standard_price
                for product in self
            }
        value_by_product_id = {p.id: p.qty_available * std_price_by_product_id.get(p.id, 0) for p in self}
        return std_price_by_product_id, value_by_product_id

    def _run_average_batch(self, at_date=None, lot=None, force_recompute=False):
        std_price_by_product_id = {}
        value_by_product_id = {}
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
        if at_date:
            moves_domain &= Domain([
                ('date', '<=', at_date),
            ])

        last_manual_value_by_product = self._get_last_product_value(at_date, lot=lot)
        oldest_manual_value = min(pv.date for pv in last_manual_value_by_product.values()) if last_manual_value_by_product else False
        if oldest_manual_value:
            moves_domain &= Domain([('date', '>=', oldest_manual_value)])

        for manual_value in last_manual_value_by_product.values():
            product = manual_value.product_id
            if lot:
                quantity = lot.with_context(to_date=manual_value.date, skip_in_progress=True).product_qty
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
            quantity = quantity_by_product_id.get(product.id, 0)
            average_cost = std_price_by_product_id.get(product.id, 0)
            value = value_by_product_id.get(product.id, 0)

            product_moves = self.env['stock.move'].browse(move_ids)
            for moves_batch in split_every(batch_size, product_moves.ids):
                moves_batch = self.env['stock.move'].browse(moves_batch)
                moves_batch.fetch(move_fields)
                moves_batch.move_line_ids.fetch(move_line_fields)
                for move in moves_batch:
                    if move.is_in or move.is_dropship:
                        in_qty = move._get_valued_qty()
                        in_value = move.value
                        if at_date or move.is_dropship:
                            in_value = move._get_value(at_date=at_date)
                        if lot:
                            lot_qty = move._get_valued_qty(lot)
                            in_value = (in_value * lot_qty / in_qty) if in_qty else 0
                            in_qty = lot_qty
                        previous_qty = quantity
                        quantity += in_qty
                        # Regular case, value from accumulation
                        if previous_qty > 0:
                            value += in_value
                            average_cost = value / quantity
                        # From negative quantity case, value from last_in
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
                        value -= out_value
                        quantity -= out_qty

                self.env['stock.move'].invalidate_model()  # Avoid keeping too many records in cache
                self.env['stock.move.line'].invalidate_model()

            std_price_by_product_id[product.id] = average_cost
            value_by_product_id[product.id] = value

        return std_price_by_product_id, value_by_product_id

    def _run_fifo_batch(self, at_date=None, lot=None, location=None):
        std_price_by_product_id = {}
        value_by_product_id = {}
        for product in self:
            quantity = product.qty_available
            if lot:
                quantity = lot.product_qty
            value = product._run_fifo(quantity, lot, at_date, location)
            std_price = value / quantity if quantity else 0
            std_price_by_product_id[product.id] = std_price
            value_by_product_id[product.id] = value

        return std_price_by_product_id, value_by_product_id

    def _run_fifo(self, quantity, lot=None, at_date=None, location=None):
        """ Returns the value for the next outgoing product base on the qty give as argument."""
        self.ensure_one()
        if self.uom_id.compare(quantity, 0) <= 0:
            if at_date:
                last_in = self._get_last_in(at_date)
                return quantity * (last_in._get_price_unit() if last_in else self.standard_price)
            return quantity * self.standard_price
        external_location = location and location.is_valued_external

        fifo_cost = 0
        fifo_stack, qty_on_first_move = self._run_fifo_get_stack(lot=lot, at_date=at_date, location=location)
        last_move = False
        # Going up to get the quantity in the argument
        while quantity > 0 and fifo_stack:
            move = fifo_stack.pop(0)
            last_move = move
            move_value = move.value
            if at_date:
                move_value = move._get_value(at_date=at_date)
            if qty_on_first_move:
                valued_qty = move._get_valued_qty()
                in_qty = qty_on_first_move
                in_value = move_value * in_qty / valued_qty
                qty_on_first_move = 0
            else:
                in_qty = move._get_valued_qty()
                in_value = move_value
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

    def _run_fifo_get_stack(self, lot=None, at_date=None, location=None):
        # TODO: return a list of tuple (move, valued_qty) instead
        external_location = location and location.is_valued_external
        fifo_stack = []
        fifo_stack_size = 0
        if location:
            self = self.with_context(location=location.ids)  # noqa: PLW0642
        if lot:
            fifo_stack_size = lot.product_qty
        else:
            fifo_stack_size = self._with_valuation_context().with_context(to_date=at_date).qty_available
        if self.env.context.get('fifo_qty_already_processed'):
            # When validating multiple moves at the same time, the qty_available won't be up to date yet
            fifo_stack_size -= self.env.context['fifo_qty_already_processed']
        if self.uom_id.compare(fifo_stack_size, 0) <= 0:
            return fifo_stack, 0

        moves_domain = Domain([
            ('product_id', '=', self.id),
            ('company_id', '=', self.env.company.id)
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

        # Arbitrary limit as we can't guess how many moves correspond to the qty_available, but avoid fetching all moves at the same time.
        initial_limit = 100
        moves_in = self.env['stock.move'].search(moves_domain, order='date desc, id desc', limit=initial_limit)

        remaining_qty_on_first_stack_move = 0
        current_offset = 0
        # Go to the bottom of the stack
        while self.uom_id.compare(fifo_stack_size, 0) > 0 and moves_in:
            move = moves_in[0]
            moves_in = moves_in[1:]
            in_qty = move._get_valued_qty()
            fifo_stack.append(move)
            remaining_qty_on_first_stack_move = min(in_qty, fifo_stack_size)
            fifo_stack_size -= in_qty
            if self.uom_id.compare(fifo_stack_size, 0) > 0 and not moves_in:
                # We need to fetch more moves
                current_offset += 1
                moves_in = self.env['stock.move'].search(moves_domain, order='date desc, id desc', offset=current_offset * initial_limit, limit=initial_limit)
        fifo_stack.reverse()
        return fifo_stack, remaining_qty_on_first_stack_move

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        # TODO: Add extra value and extra quantity kwargs to avoid total recomputation
        products_by_cost_method = defaultdict(set)
        for product in self:
            if product.lot_valuated:
                product.sudo().with_context(disable_auto_revaluation=True).standard_price = product.avg_cost
                continue
            products_by_cost_method[product.cost_method].add(product.id)
        for cost_method, product_ids in products_by_cost_method.items():
            products = self.env['product.product'].browse(product_ids)
            if cost_method == 'standard':
                continue
            if cost_method == 'fifo':
                for product in products:
                    qty_available = product._with_valuation_context().qty_available
                    if product.uom_id.compare(qty_available, 0) > 0:
                        product.sudo().with_context(disable_auto_revaluation=True).standard_price = product.total_value / qty_available
                    elif last_in := product._get_last_in():
                        if last_in_price_unit := last_in._get_price_unit():
                            product.sudo().with_context(disable_auto_revaluation=True).standard_price = last_in_price_unit
                continue
            if cost_method == 'average':
                new_standard_price_by_product = self._run_average_batch(force_recompute=True)[0]
                for product in products:
                    if product.id in new_standard_price_by_product:
                        product.with_context(disable_auto_revaluation=True).sudo().standard_price = new_standard_price_by_product[product.id]

    # -------------------------------------------------------------------------
    # Old to remove
    # -------------------------------------------------------------------------
    def _run_avco(self, at_date=None, lot=None, method="realtime"):
        self.ensure_one()
        price_unit, value = self._run_average_batch(at_date=at_date, lot=lot, force_recompute=True)
        return price_unit.get(self.id, 0), value.get(self.id, 0)

    def _get_value_from_lots(self):
        return 0


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
        help="""Periodic: The accounting entries are suggested manually in the inventory valuation report.
        Perpetual: An accounting entry is automatically created to value the inventory when a product is billed or invoiced.
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
    account_stock_variation_id = fields.Many2one(
        'account.account', string="Stock Variation Account", readonly=False,
        related="property_stock_valuation_account_id.account_stock_variation_id")

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
            products_to_update._update_standard_price()
        products_lot_valuated = products_to_update.filtered(lambda p: p.lot_valuated)
        if products_lot_valuated:
            self.env['stock.lot'].sudo().search([('product_id', 'in', products_lot_valuated.ids)])._update_standard_price()
        return res
