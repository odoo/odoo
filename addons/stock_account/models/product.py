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
        compute='_compute_valuation', search='_search_valuation',
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

    def _search_valuation(self, operator, value):
        if operator != '=' or value not in ['periodic', 'real_time']:
            raise UserError(_("Invalid search on valuation"))
        domain_categ = Domain([('categ_id.property_valuation', operator, value)])
        domain_company = Domain(['|', ('categ_id.property_valuation', '=', False), ('categ_id', '=', False), ('company_id.inventory_valuation', operator, value)])
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
        product_to_update = set()
        if 'categ_id' in vals:
            category = self.env['product.category'].browse(vals['categ_id'])
            valuation = category.property_valuation if category else self.env.company.inventory_valuation
            for product in self:
                if product.valuation != valuation:
                    product_to_update.update(product.product_variant_ids.ids)
        res = super().write(vals)
        if 'lot_valuated' in vals:
            self.env['stock.lot'].search([
                ('product_id', 'in', self.product_variant_ids.ids),
            ])._update_standard_price()
        if 'product_to_update':
            self.env['product.product'].browse(product_to_update)._update_standard_price()
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
    @api.depends('cost_method', 'stock_move_ids.value')
    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id

        for product in self:
            at_date = fields.Datetime.to_datetime(product.env.context.get('to_date'))
            qty_available = product.sudo(False).with_context(at_date=at_date).qty_available
            if product.lot_valuated:
                product.total_value = product._get_value_from_lots()
            elif product.cost_method == 'standard':
                standard_price = product.standard_price
                if at_date:
                    standard_price = product._get_standard_price_at_date(at_date)
                product.total_value = standard_price * qty_available
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

<<<<<<< 7718737a5449f12cad9a0d0061709ac7ce8b55a2
    def _change_standard_price(self, old_price):
||||||| 44c993129241313c2011c6fff39478cc6791ae0f
    def _get_valuation_layer_group_domain(self):
        company_id = self.env.company.id
        domain = [
            *self.env['stock.valuation.layer']._check_company_domain(company_id),
            ('product_id', 'in', self.ids),
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        return domain

    def _get_valuation_layer_group_fields_aggregate(self):
        return ['value:sum', 'quantity:sum']

    def _get_valuation_layer_groups(self):
        domain = self._get_valuation_layer_group_domain()
        group_fields_aggregate = self._get_valuation_layer_group_fields_aggregate()
        return self.env['stock.valuation.layer']._read_group(
            domain,
            groupby=['product_id'],
            aggregates=group_fields_aggregate,
        )

    def _prepare_valuation_layer_field_values(self, aggregates):
        self.ensure_one()
        value_sum, quantity_sum = aggregates
        value_svl = self.env.company.currency_id.round(value_sum)
        avg_cost = 0
        if not float_is_zero(quantity_sum, precision_rounding=self.uom_id.rounding):
            avg_cost = value_svl / quantity_sum
        return {
            "value_svl": value_svl,
            "quantity_svl": quantity_sum,
            "avg_cost": avg_cost,
            "total_value": avg_cost * self.sudo(False).qty_available
        }

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company')
    def _compute_value_svl(self):
        """Compute totals of multiple svl related values"""
        self.company_currency_id = self.env.company.currency_id
        valuation_layer_groups = self._get_valuation_layer_groups()
        # Browse all products and compute products' quantities_dict in batch.
        group_mapping = {product: aggregates for product, *aggregates in valuation_layer_groups}
=======
    def _get_valuation_layer_group_domain(self):
        company_id = self.env.company.id
        domain = [
            *self.env['stock.valuation.layer']._check_company_domain(company_id),
            ('product_id', 'in', self.ids),
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        return domain

    def _get_valuation_layer_group_fields_aggregate(self):
        return ['value:sum', 'quantity:sum']

    def _get_valuation_layer_groups(self):
        domain = self._get_valuation_layer_group_domain()
        group_fields_aggregate = self._get_valuation_layer_group_fields_aggregate()
        return self.env['stock.valuation.layer']._read_group(
            domain,
            groupby=['product_id'],
            aggregates=group_fields_aggregate,
        )

    def _prepare_valuation_layer_field_values(self, aggregates):
        self.ensure_one()
        value_sum, quantity_sum = aggregates
        value_svl = self.env.company.currency_id.round(value_sum)
        avg_cost = 0
        if not float_is_zero(quantity_sum, precision_rounding=self.uom_id.rounding):
            avg_cost = value_svl / quantity_sum
        return {
            "value_svl": value_svl,
            "quantity_svl": quantity_sum,
            "avg_cost": avg_cost,
            "total_value": avg_cost * self.sudo(False).qty_available if avg_cost else 0
        }

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company')
    def _compute_value_svl(self):
        """Compute totals of multiple svl related values"""
        self.company_currency_id = self.env.company.currency_id
        valuation_layer_groups = self._get_valuation_layer_groups()
        # Browse all products and compute products' quantities_dict in batch.
        group_mapping = {product: aggregates for product, *aggregates in valuation_layer_groups}
>>>>>>> fc1660f08a23e4b4debf5787e6ab7d3d792aa295
        for product in self:
            if product.cost_method == 'fifo' or product.standard_price == old_price.get(product):
                continue
            self.env['product.value'].sudo().create({
                'product_id': product.id,
                'value': product.standard_price,
                'company_id': product.company_id.id or self.env.company.id,
                'date': fields.Datetime.now(),
                'description': _('Price update from %(old_price)s to %(new_price)s by %(user)s',
                    old_price=old_price.get(product), new_price=product.standard_price, user=self.env.user.name)
            })
        return

<<<<<<< 7718737a5449f12cad9a0d0061709ac7ce8b55a2
    def _get_standard_price_at_date(self, date):
||||||| 44c993129241313c2011c6fff39478cc6791ae0f
    # TODO remove in master
    def _create_fifo_vacuum_anglo_saxon_expense_entry(self, vacuum_svl, svl_to_vacuum):
        """ When product is delivered and invoiced while you don't have units in stock anymore, there are chances of that
            product getting undervalued/overvalued. So, we should nevertheless take into account the fact that the product has
            already been delivered and invoiced to the customer by posting the value difference in the expense account also.
            Consider the below case where product is getting undervalued:

            You bought 8 units @ 10$ -> You have a stock valuation of 8 units, unit cost 10.
            Then you deliver 10 units of the product.
            You assumed the missing 2 should go out at a value of 10$ but you are not sure yet as it hasn't been bought in Odoo yet.
            Afterwards, you buy missing 2 units of the same product at 12$ instead of expected 10$.
            In case the product has been undervalued when delivered without stock, the vacuum entry is the following one (this entry already takes place):

            Account                         | Debit   | Credit
            ===================================================
            Stock Valuation                 | 0.00     | 4.00
            Stock Interim (Delivered)       | 4.00     | 0.00

            So, on delivering product with different price, We should create additional journal items like:
            Account                         | Debit    | Credit
            ===================================================
            Stock Interim (Delivered)       | 0.00     | 4.00
            Expenses Revaluation            | 4.00     | 0.00
        """
        if not vacuum_svl.company_id.anglo_saxon_accounting or not svl_to_vacuum.stock_move_id._is_out():
            return False
        AccountMove = self.env['account.move'].sudo()
        account_move_lines = svl_to_vacuum.account_move_id.line_ids
        # Find related customer invoice where product is delivered while you don't have units in stock anymore
        reconciled_line_ids = list(set(account_move_lines._reconciled_lines()) - set(account_move_lines.ids))
        account_move = AccountMove.search([('line_ids','in', reconciled_line_ids)], limit=1)
        # If delivered quantity is not invoiced then no need to create this entry
        if not account_move:
            return False
        accounts = svl_to_vacuum.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=account_move.fiscal_position_id)
        if not accounts.get('stock_output') or not accounts.get('expense'):
            return False
        description = "Expenses %s" % (vacuum_svl.description)
        move_lines = vacuum_svl.stock_move_id._prepare_account_move_line(
            vacuum_svl.quantity, vacuum_svl.value * -1,
            accounts['stock_output'].id, accounts['expense'].id,
            vacuum_svl.id, description)
        new_account_move = AccountMove.sudo().create({
            'journal_id': accounts['stock_journal'].id,
            'line_ids': move_lines,
            'date': self._context.get('force_period_date', fields.Date.context_today(self)),
            'ref': description,
            'stock_move_id': vacuum_svl.stock_move_id.id,
            'move_type': 'entry',
        })
        new_account_move._post()
        to_reconcile_account_move_lines = vacuum_svl.account_move_id.line_ids.filtered(lambda l: not l.reconciled and l.account_id == accounts['stock_output'] and l.account_id.reconcile)
        to_reconcile_account_move_lines += new_account_move.line_ids.filtered(lambda l: not l.reconciled and l.account_id == accounts['stock_output'] and l.account_id.reconcile)
        return to_reconcile_account_move_lines.reconcile()

    def _update_lots_standard_price(self):
        grouped_lots = self.env['stock.lot']._read_group(
            [('product_id', 'in', self.ids), ('product_id.lot_valuated', '=', True)],
            ['product_id'], ['id:recordset']
        )
        for product, lots in grouped_lots:
            lots.with_context(disable_auto_svl=True).write({"standard_price": product.standard_price})

    @api.model
    def _svl_empty_stock(self, description, product_category=None, product_template=None):
        impacted_product_ids = []
        impacted_products = self.env['product.product']
        products_orig_quantity_svl = {}

        # get the impacted products
        domain = [('is_storable', '=', True)]
        if product_category is not None:
            domain += [('categ_id', '=', product_category.id)]
        elif product_template is not None:
            domain += [('product_tmpl_id', '=', product_template.id)]
        else:
            raise ValueError()
        products = self.env['product.product'].search_read(domain, ['quantity_svl'])
        for product in products:
            impacted_product_ids.append(product['id'])
            products_orig_quantity_svl[product['id']] = product['quantity_svl']
        impacted_products |= self.env['product.product'].browse(impacted_product_ids)

        # empty out the stock for the impacted products
        empty_stock_svl_list = []
        lots_by_product = defaultdict(lambda: self.env['stock.lot'])
        res = self.env["stock.valuation.layer"]._read_group(
            [("product_id", "in", impacted_products.ids), ("remaining_qty", "!=", 0)],
            ["product_id"],
            ["lot_id:recordset"],
        )
        for group in res:
            lots_by_product[group[0].id] |= group[1]
        for product in impacted_products:
            # FIXME sle: why not use products_orig_quantity_svl here?
            if float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                # FIXME: create an empty layer to track the change?
                continue
            if product.lot_valuated:
                if float_compare(product.quantity_svl, 0, precision_rounding=product.uom_id.rounding) > 0:
                    for lot in lots_by_product[product.id]:
                        svsl_vals = product._prepare_out_svl_vals(lot.quantity_svl, self.env.company, lot=lot)
                        svsl_vals['description'] = description + svsl_vals.pop('rounding_adjustment', '')
                        svsl_vals['company_id'] = self.env.company.id
                        empty_stock_svl_list.append(svsl_vals)
                else:
                    for lot in lots_by_product[product.id]:
                        svsl_vals = product._prepare_in_svl_vals(abs(lot.quantity_svl), lot.value_svl / lot.quantity_svl, lot=lot)
                        svsl_vals['description'] = description + svsl_vals.pop('rounding_adjustment', '')
                        svsl_vals['company_id'] = self.env.company.id
                        empty_stock_svl_list.append(svsl_vals)
            else:
                if float_compare(product.quantity_svl, 0, precision_rounding=product.uom_id.rounding) > 0:
                    svsl_vals = product._prepare_out_svl_vals(product.quantity_svl, self.env.company)
                else:
                    svsl_vals = product._prepare_in_svl_vals(abs(product.quantity_svl), product.value_svl / product.quantity_svl)
                svsl_vals['description'] = description + svsl_vals.pop('rounding_adjustment', '')
                svsl_vals['company_id'] = self.env.company.id
                empty_stock_svl_list.append(svsl_vals)
        return empty_stock_svl_list, products_orig_quantity_svl, impacted_products

    def _svl_replenish_stock(self, description, products_orig_quantity_svl):
        refill_stock_svl_list = []
        lot_by_product = defaultdict(lambda: defaultdict(float))
        neg_lots = self.env['stock.quant']._read_group([
            ('product_id', 'in', self.product_variant_ids.ids),
            ('lot_id', '!=', False),
            ], ['product_id', 'location_id', 'lot_id'], ['quantity:sum'],
            having=[('quantity:sum', '<', 0)])
        lots = self.env['stock.quant']._read_group([
            ('product_id', 'in', self.product_variant_ids.ids),
            ('lot_id', '!=', False),
            ], ['product_id', 'location_id', 'lot_id'], ['quantity:sum'],
            having=[('quantity:sum', '>', 0)])
        for product, location, lot, qty in lots:
            if location._should_be_valued():
                lot_by_product[product][lot] += qty
        for product, location, lot, qty in neg_lots:
            if location._should_be_valued():
                raise UserError(_(
                    "Lot %(lot)s has a negative quantity in stock.\n"
                    "Correct this quantity before enabling/disabling lot valuation.",
                    lot=lot.display_name
                ))
        lot_valuated_products = self.filtered("lot_valuated")
        if lot_valuated_products:
            no_lot_quants = self.env['stock.quant']._read_group([
                ('product_id', 'in', lot_valuated_products.ids),
                ('lot_id', '=', False),
                ('quantity', '!=', 0),
            ], ['product_id', 'location_id'])
            for product, location in no_lot_quants:
                if location._should_be_valued():
                    raise UserError(_(
                        "Product %(product)s has quantity in valued location %(location)s without any lot.\n"
                        "Please assign lots to all your quantities before enabling lot valuation.",
                        product=product.display_name,
                        location=location.display_name
                    ))

        for product in self:
            quantity_svl = products_orig_quantity_svl[product.id]
            if not quantity_svl:
                continue
            rounding = product.uom_id.rounding
            price_unit = product.standard_price
            if not product.lot_valuated:
                lot_by_product[product] = {False: quantity_svl}
            for lot, qty in lot_by_product[product].items():
                if float_compare(quantity_svl, 0, precision_rounding=rounding) > 0:
                    qty_to_remove = min(qty, quantity_svl)
                    quantity_svl -= qty_to_remove
                    svl_vals = product._prepare_in_svl_vals(qty_to_remove, price_unit, lot=lot)

                else:
                    svl_vals = product._prepare_out_svl_vals(abs(quantity_svl), self.env.company, lot=lot)
                svl_vals['description'] = description
                svl_vals['company_id'] = self.env.company.id
                refill_stock_svl_list.append(svl_vals)
                if float_is_zero(quantity_svl, precision_rounding=rounding):
                    break
        return refill_stock_svl_list

    @api.model
    def _svl_empty_stock_am(self, stock_valuation_layers):
        move_vals_list = []
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in stock_valuation_layers.mapped('product_id')}
        for out_stock_valuation_layer in stock_valuation_layers:
            product = out_stock_valuation_layer.product_id
            stock_input_account = product_accounts[product.id].get('stock_input')
            if not stock_input_account:
                raise UserError(_('You don\'t have any stock input account defined on your product category. You must define one before processing this operation.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
            if not product_accounts[product.id].get('stock_output'):
                raise UserError(
                    _('You don\'t have any output valuation account defined on your product '
                      'category. You must define one before processing this operation.')
                )

            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            orig_qtys = self.env.context.get('products_orig_quantity_svl')
            if orig_qtys and float_compare(orig_qtys[product.id], 0, precision_digits=precision) < 1:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['stock_output'].id
            else:
                debit_account_id = stock_input_account.id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
            value = out_stock_valuation_layer.value
            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': self.env.company.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [out_stock_valuation_layer.id])],
                'line_ids': [(0, 0, {
                    'name': out_stock_valuation_layer.description,
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': out_stock_valuation_layer.description,
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                })],
                'move_type': 'entry',
            }
            move_vals_list.append(move_vals)
        return move_vals_list

    def _svl_replenish_stock_am(self, stock_valuation_layers):
        move_vals_list = []
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in stock_valuation_layers.mapped('product_id')}
        for out_stock_valuation_layer in stock_valuation_layers:
            product = out_stock_valuation_layer.product_id
            if not product_accounts[product.id].get('stock_input'):
                raise UserError(_('You don\'t have any input valuation account defined on your product category. You must define one before processing this operation.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
            if not product_accounts[product.id].get('stock_output'):
                raise UserError(
                    _('You don\'t have any output valuation account defined on your product '
                      'category. You must define one before processing this operation.')
                )

            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(out_stock_valuation_layer.quantity, 0, precision_digits=precision) == 1:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['stock_input'].id
            else:
                debit_account_id = product_accounts[product.id]['stock_output'].id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id

            value = out_stock_valuation_layer.value
            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': self.env.company.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [out_stock_valuation_layer.id])],
                'line_ids': [(0, 0, {
                    'name': out_stock_valuation_layer.description,
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': out_stock_valuation_layer.description,
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                })],
                'move_type': 'entry',
            }
            move_vals_list.append(move_vals)
        return move_vals_list

    # -------------------------------------------------------------------------
    # Anglo saxon helpers
    # -------------------------------------------------------------------------
    def _stock_account_get_anglo_saxon_price_unit(self, uom=False):
        price = self.standard_price
        if not self or not uom or self.uom_id.id == uom.id:
            return price or 0.0
        return self.uom_id._compute_price(price, uom)

    def _compute_average_price(self, qty_invoiced, qty_to_invoice, stock_moves, is_returned=False):
        """Go over the valuation layers of `stock_moves` to value `qty_to_invoice` while taking
        care of ignoring `qty_invoiced`. If `qty_to_invoice` is greater than what's possible to
        value with the valuation layers, use the product's standard price.

        :param qty_invoiced: quantity already invoiced
        :param qty_to_invoice: quantity to invoice
        :param stock_moves: recordset of `stock.move`
        :param is_returned: if True, consider the incoming moves
        :returns: the anglo saxon price unit
        :rtype: float
        """
=======
    # TODO remove in master
    def _create_fifo_vacuum_anglo_saxon_expense_entry(self, vacuum_svl, svl_to_vacuum):
        """ When product is delivered and invoiced while you don't have units in stock anymore, there are chances of that
            product getting undervalued/overvalued. So, we should nevertheless take into account the fact that the product has
            already been delivered and invoiced to the customer by posting the value difference in the expense account also.
            Consider the below case where product is getting undervalued:

            You bought 8 units @ 10$ -> You have a stock valuation of 8 units, unit cost 10.
            Then you deliver 10 units of the product.
            You assumed the missing 2 should go out at a value of 10$ but you are not sure yet as it hasn't been bought in Odoo yet.
            Afterwards, you buy missing 2 units of the same product at 12$ instead of expected 10$.
            In case the product has been undervalued when delivered without stock, the vacuum entry is the following one (this entry already takes place):

            Account                         | Debit   | Credit
            ===================================================
            Stock Valuation                 | 0.00     | 4.00
            Stock Interim (Delivered)       | 4.00     | 0.00

            So, on delivering product with different price, We should create additional journal items like:
            Account                         | Debit    | Credit
            ===================================================
            Stock Interim (Delivered)       | 0.00     | 4.00
            Expenses Revaluation            | 4.00     | 0.00
        """
        if not vacuum_svl.company_id.anglo_saxon_accounting or not svl_to_vacuum.stock_move_id._is_out():
            return False
        AccountMove = self.env['account.move'].sudo()
        account_move_lines = svl_to_vacuum.account_move_id.line_ids
        # Find related customer invoice where product is delivered while you don't have units in stock anymore
        reconciled_line_ids = list(set(account_move_lines._reconciled_lines()) - set(account_move_lines.ids))
        account_move = AccountMove.search([('line_ids','in', reconciled_line_ids)], limit=1)
        # If delivered quantity is not invoiced then no need to create this entry
        if not account_move:
            return False
        accounts = svl_to_vacuum.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=account_move.fiscal_position_id)
        if not accounts.get('stock_output') or not accounts.get('expense'):
            return False
        description = "Expenses %s" % (vacuum_svl.description)
        move_lines = vacuum_svl.stock_move_id._prepare_account_move_line(
            vacuum_svl.quantity, vacuum_svl.value * -1,
            accounts['stock_output'].id, accounts['expense'].id,
            vacuum_svl.id, description)
        new_account_move = AccountMove.sudo().create({
            'journal_id': accounts['stock_journal'].id,
            'line_ids': move_lines,
            'date': self._context.get('force_period_date', fields.Date.context_today(self)),
            'ref': description,
            'stock_move_id': vacuum_svl.stock_move_id.id,
            'move_type': 'entry',
        })
        new_account_move._post()
        to_reconcile_account_move_lines = vacuum_svl.account_move_id.line_ids.filtered(lambda l: not l.reconciled and l.account_id == accounts['stock_output'] and l.account_id.reconcile)
        to_reconcile_account_move_lines += new_account_move.line_ids.filtered(lambda l: not l.reconciled and l.account_id == accounts['stock_output'] and l.account_id.reconcile)
        return to_reconcile_account_move_lines.reconcile()

    def _update_lots_standard_price(self):
        grouped_lots = self.env['stock.lot']._read_group(
            [('product_id', 'in', self.ids), ('product_id.lot_valuated', '=', True)],
            ['product_id'], ['id:recordset']
        )
        for product, lots in grouped_lots:
            lots.with_context(disable_auto_svl=True).write({"standard_price": product.standard_price})

    @api.model
    def _svl_empty_stock(self, description, product_category=None, product_template=None):
        impacted_product_ids = []
        impacted_products = self.env['product.product']
        products_orig_quantity_svl = {}

        # get the impacted products
        domain = [('is_storable', '=', True)]
        if product_category is not None:
            domain += [('categ_id', '=', product_category.id)]
        elif product_template is not None:
            domain += [('product_tmpl_id', '=', product_template.id)]
        else:
            raise ValueError()
        products = self.env['product.product'].search_read(domain, ['quantity_svl'])
        for product in products:
            impacted_product_ids.append(product['id'])
            products_orig_quantity_svl[product['id']] = product['quantity_svl']
        impacted_products |= self.env['product.product'].browse(impacted_product_ids)

        # empty out the stock for the impacted products
        empty_stock_svl_list = []
        lots_by_product = defaultdict(lambda: self.env['stock.lot'])
        res = self.env["stock.valuation.layer"]._read_group(
            [("product_id", "in", impacted_products.ids), ("remaining_qty", "!=", 0)],
            ["product_id"],
            ["lot_id:recordset"],
        )
        for group in res:
            lots_by_product[group[0].id] |= group[1]
        for product in impacted_products:
            # FIXME sle: why not use products_orig_quantity_svl here?
            if float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                # FIXME: create an empty layer to track the change?
                continue
            if product.lot_valuated:
                if float_compare(product.quantity_svl, 0, precision_rounding=product.uom_id.rounding) > 0:
                    for lot in lots_by_product[product.id]:
                        svsl_vals = product._prepare_out_svl_vals(lot.quantity_svl, self.env.company, lot=lot)
                        svsl_vals['description'] = description + svsl_vals.pop('rounding_adjustment', '')
                        svsl_vals['company_id'] = self.env.company.id
                        empty_stock_svl_list.append(svsl_vals)
                else:
                    for lot in lots_by_product[product.id]:
                        svsl_vals = product._prepare_in_svl_vals(abs(lot.quantity_svl), lot.value_svl / lot.quantity_svl, lot=lot)
                        svsl_vals['description'] = description + svsl_vals.pop('rounding_adjustment', '')
                        svsl_vals['company_id'] = self.env.company.id
                        empty_stock_svl_list.append(svsl_vals)
            else:
                if float_compare(product.quantity_svl, 0, precision_rounding=product.uom_id.rounding) > 0:
                    svsl_vals = product._prepare_out_svl_vals(product.quantity_svl, self.env.company)
                else:
                    svsl_vals = product._prepare_in_svl_vals(abs(product.quantity_svl), product.value_svl / product.quantity_svl)
                svsl_vals['description'] = description + svsl_vals.pop('rounding_adjustment', '')
                svsl_vals['company_id'] = self.env.company.id
                empty_stock_svl_list.append(svsl_vals)
        return empty_stock_svl_list, products_orig_quantity_svl, impacted_products

    def _svl_replenish_stock(self, description, products_orig_quantity_svl):
        refill_stock_svl_list = []
        lot_by_product = defaultdict(lambda: defaultdict(float))
        neg_lots = self.env['stock.quant']._read_group([
            ('product_id', 'in', self.product_tmpl_id.product_variant_ids.ids),
            ('lot_id', '!=', False),
            ], ['product_id', 'location_id', 'lot_id'], ['quantity:sum'],
            having=[('quantity:sum', '<', 0)])
        lots = self.env['stock.quant']._read_group([
            ('product_id', 'in', self.product_tmpl_id.product_variant_ids.ids),
            ('lot_id', '!=', False),
            ], ['product_id', 'location_id', 'lot_id'], ['quantity:sum'],
            having=[('quantity:sum', '>', 0)])
        for product, location, lot, qty in lots:
            if location._should_be_valued():
                lot_by_product[product][lot] += qty
        for product, location, lot, qty in neg_lots:
            if location._should_be_valued():
                raise UserError(_(
                    "Lot %(lot)s has a negative quantity in stock.\n"
                    "Correct this quantity before enabling/disabling lot valuation.",
                    lot=lot.display_name
                ))
        lot_valuated_products = self.filtered("lot_valuated")
        if lot_valuated_products:
            no_lot_quants = self.env['stock.quant']._read_group([
                ('product_id', 'in', lot_valuated_products.ids),
                ('lot_id', '=', False),
                ('quantity', '!=', 0),
            ], ['product_id', 'location_id'])
            for product, location in no_lot_quants:
                if location._should_be_valued():
                    raise UserError(_(
                        "Product %(product)s has quantity in valued location %(location)s without any lot.\n"
                        "Please assign lots to all your quantities before enabling lot valuation.",
                        product=product.display_name,
                        location=location.display_name
                    ))

        for product in self:
            quantity_svl = products_orig_quantity_svl[product.id]
            if not quantity_svl:
                continue
            rounding = product.uom_id.rounding
            price_unit = product.standard_price
            if not product.lot_valuated:
                lot_by_product[product] = {False: quantity_svl}
            for lot, qty in lot_by_product[product].items():
                if float_compare(quantity_svl, 0, precision_rounding=rounding) > 0:
                    qty_to_remove = min(qty, quantity_svl)
                    quantity_svl -= qty_to_remove
                    svl_vals = product._prepare_in_svl_vals(qty_to_remove, price_unit, lot=lot)

                else:
                    svl_vals = product._prepare_out_svl_vals(abs(quantity_svl), self.env.company, lot=lot)
                svl_vals['description'] = description
                svl_vals['company_id'] = self.env.company.id
                refill_stock_svl_list.append(svl_vals)
                if float_is_zero(quantity_svl, precision_rounding=rounding):
                    break
        return refill_stock_svl_list

    @api.model
    def _svl_empty_stock_am(self, stock_valuation_layers):
        move_vals_list = []
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in stock_valuation_layers.mapped('product_id')}
        for out_stock_valuation_layer in stock_valuation_layers:
            product = out_stock_valuation_layer.product_id
            stock_input_account = product_accounts[product.id].get('stock_input')
            if not stock_input_account:
                raise UserError(_('You don\'t have any stock input account defined on your product category. You must define one before processing this operation.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
            if not product_accounts[product.id].get('stock_output'):
                raise UserError(
                    _('You don\'t have any output valuation account defined on your product '
                      'category. You must define one before processing this operation.')
                )

            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            orig_qtys = self.env.context.get('products_orig_quantity_svl')
            if orig_qtys and float_compare(orig_qtys[product.id], 0, precision_digits=precision) < 1:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['stock_output'].id
            else:
                debit_account_id = stock_input_account.id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
            value = out_stock_valuation_layer.value
            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': self.env.company.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [out_stock_valuation_layer.id])],
                'line_ids': [(0, 0, {
                    'name': out_stock_valuation_layer.description,
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': out_stock_valuation_layer.description,
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                })],
                'move_type': 'entry',
            }
            move_vals_list.append(move_vals)
        return move_vals_list

    def _svl_replenish_stock_am(self, stock_valuation_layers):
        move_vals_list = []
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in stock_valuation_layers.mapped('product_id')}
        for out_stock_valuation_layer in stock_valuation_layers:
            product = out_stock_valuation_layer.product_id
            if not product_accounts[product.id].get('stock_input'):
                raise UserError(_('You don\'t have any input valuation account defined on your product category. You must define one before processing this operation.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
            if not product_accounts[product.id].get('stock_output'):
                raise UserError(
                    _('You don\'t have any output valuation account defined on your product '
                      'category. You must define one before processing this operation.')
                )

            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(out_stock_valuation_layer.quantity, 0, precision_digits=precision) == 1:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['stock_input'].id
            else:
                debit_account_id = product_accounts[product.id]['stock_output'].id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id

            value = out_stock_valuation_layer.value
            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': self.env.company.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [out_stock_valuation_layer.id])],
                'line_ids': [(0, 0, {
                    'name': out_stock_valuation_layer.description,
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': out_stock_valuation_layer.description,
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                })],
                'move_type': 'entry',
            }
            move_vals_list.append(move_vals)
        return move_vals_list

    # -------------------------------------------------------------------------
    # Anglo saxon helpers
    # -------------------------------------------------------------------------
    def _stock_account_get_anglo_saxon_price_unit(self, uom=False):
        price = self.standard_price
        if not self or not uom or self.uom_id.id == uom.id:
            return price or 0.0
        return self.uom_id._compute_price(price, uom)

    def _compute_average_price(self, qty_invoiced, qty_to_invoice, stock_moves, is_returned=False):
        """Go over the valuation layers of `stock_moves` to value `qty_to_invoice` while taking
        care of ignoring `qty_invoiced`. If `qty_to_invoice` is greater than what's possible to
        value with the valuation layers, use the product's standard price.

        :param qty_invoiced: quantity already invoiced
        :param qty_to_invoice: quantity to invoice
        :param stock_moves: recordset of `stock.move`
        :param is_returned: if True, consider the incoming moves
        :returns: the anglo saxon price unit
        :rtype: float
        """
>>>>>>> fc1660f08a23e4b4debf5787e6ab7d3d792aa295
        self.ensure_one()
        product_value = self.env['product.value'].search([
            ('product_id', '=', self.id),
            ('date', '<=', date),
            ('move_id', '=', False),
            ('lot_id', '=', False),
        ], limit=1, order="date DESC, id DESC")
        if not product_value:
            # If there is no history then get the first value
            product_value = self.env['product.value'].search([
                ('product_id', '=', self.id),
                ('move_id', '=', False),
                ('lot_id', '=', False),
            ], limit=1, order="date, id")
        return product_value.value if product_value else self.standard_price

    def _get_value_from_lots(self):
        lots = self.env['stock.lot'].search([
            ('product_id', 'in', self.ids),
            ('product_qty', '!=', 0),
        ])
        return sum(lots.mapped('total_value'))

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
            ('company_id', '=', self.env.company.id),
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

        # TODO Only browse from last product_value
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
                    lot_qty = move._get_valued_qty(lot)
                    in_value = in_value * lot_qty / in_qty
                    in_qty = lot_qty
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
                out_value = out_qty * avco_value
                if lot:
                    lot_qty = move._get_valued_qty(lot)
                    out_value = out_value * lot_qty / out_qty
                    out_qty = lot_qty
                avco_total_value -= out_value
                quantity -= out_qty

        return avco_value, avco_total_value

    def _run_fifo(self, quantity, lot=None, at_date=None, location=None):
        """ Returns the value for the next outgoing product base on the qty give as argument."""
        self.ensure_one()
        external_location = location and location.is_valued_external

        fifo_cost = 0
        fifo_stack, qty_on_first_move = self._run_fifo_get_stack(lot=lot, at_date=at_date, location=location)
        last_move = False
        # Going up to get the quantity in the argument
        while quantity > 0 and fifo_stack:
            move = fifo_stack.pop(0)
            last_move = move
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
            fifo_stack_size = int(self.with_context(to_date=at_date).qty_available)
        if fifo_stack_size <= 0:
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

        # Base limit to 100 to avoid issue with other UoM than Unit
        initial_limit = fifo_stack_size * 10
        unit_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        if unit_uom and self.uom_id != unit_uom:
            initial_limit = max(initial_limit, 100)
        moves_in = self.env['stock.move'].search(moves_domain, order='date desc, id desc', limit=initial_limit)

        remaining_qty_on_first_stack_move = 0
        current_offset = 0
        # Go to the bottom of the stack
        while fifo_stack_size > 0 and moves_in:
            move = moves_in[0]
            moves_in = moves_in[1:]
            in_qty = move._get_valued_qty()
            fifo_stack.append(move)
            remaining_qty_on_first_stack_move = min(in_qty, fifo_stack_size)
            fifo_stack_size -= in_qty
            if fifo_stack_size > 0 and not moves_in:
                # We need to fetch more moves
                current_offset += 1
                moves_in = self.env['stock.move'].search(moves_domain, order='date desc, id desc', offset=current_offset * initial_limit, limit=initial_limit)
        fifo_stack.reverse()
        return fifo_stack, remaining_qty_on_first_stack_move

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        # TODO: Add extra value and extra quantity kwargs to avoid total recomputation
        for product in self:
            if product.cost_method == 'standard':
                continue
            elif product.cost_method == 'fifo':
                fifo_price = product.total_value / product.qty_available if product.qty_available else 0
                if fifo_price != 0:
                    product.with_context(disable_auto_revaluation=True).standard_price = fifo_price
                elif last_in := self.env['stock.move'].search([('is_in', '=', True), ('product_id', '=', product.id)], order='date desc, id desc', limit=1):
                    product.with_context(disable_auto_revaluation=True).standard_price = last_in._get_price_unit()
                continue
            new_standard_price = product._run_avco()[0]
            if new_standard_price:
                product.with_context(disable_auto_revaluation=True).standard_price = new_standard_price


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

    def write(self, vals):
        products_to_update = self.env['product.product']
        if 'property_cost_method' in vals:
            updated_categories = self.filtered(lambda c: c.property_cost_method != vals['property_cost_method'])
            if updated_categories:
                products_to_update = self.env['product.product'].search([('categ_id', 'in', updated_categories.ids)])
        res = super().write(vals)
        if products_to_update:
            products_to_update._update_standard_price()
        return res
