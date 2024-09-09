# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr, float_round, float_compare
from odoo.exceptions import ValidationError
from collections import defaultdict
from datetime import datetime


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    cost_method = fields.Selection(related="categ_id.property_cost_method", readonly=True)
    valuation = fields.Selection(related="categ_id.property_valuation", readonly=True)

    def write(self, vals):
        impacted_templates = {}
        move_vals_list = []
        Product = self.env['product.product']
        SVL = self.env['stock.valuation.layer']

        if 'categ_id' in vals:
            # When a change of category implies a change of cost method, we empty out and replenish
            # the stock.
            new_product_category = self.env['product.category'].browse(vals.get('categ_id'))

            for product_template in self:
                product_template = product_template.with_company(product_template.company_id)
                valuation_impacted = False
                if product_template.cost_method != new_product_category.property_cost_method:
                    valuation_impacted = True
                if product_template.valuation != new_product_category.property_valuation:
                    valuation_impacted = True
                if valuation_impacted is False:
                    continue

                # Empty out the stock with the current cost method.
                description = _(
                    "Due to a change of product category (from %(old_category)s to %(new_category)s), the costing method has changed for product %(product)s: from %(old_method)s to %(new_method)s.",
                    old_category=product_template.categ_id.display_name,
                    new_category=new_product_category.display_name,
                    product=product_template.display_name,
                    old_method=product_template.cost_method,
                    new_method=new_product_category.property_cost_method)
                out_svl_vals_list, products_orig_quantity_svl, products = Product\
                    ._svl_empty_stock(description, product_template=product_template)
                out_stock_valuation_layers = SVL.create(out_svl_vals_list)
                if product_template.valuation == 'real_time':
                    move_vals_list += Product._svl_empty_stock_am(out_stock_valuation_layers)
                impacted_templates[product_template] = (products, description, products_orig_quantity_svl)

        res = super(ProductTemplate, self).write(vals)

        for product_template, (products, description, products_orig_quantity_svl) in impacted_templates.items():
            # Replenish the stock with the new cost method.
            in_svl_vals_list = products._svl_replenish_stock(description, products_orig_quantity_svl)
            in_stock_valuation_layers = SVL.create(in_svl_vals_list)
            if product_template.valuation == 'real_time':
                move_vals_list += Product._svl_replenish_stock_am(in_stock_valuation_layers)

        # Check access right
        if move_vals_list and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(_("The action leads to the creation of a journal entry, for which you don't have the access rights."))
        # Create the account moves.
        if move_vals_list:
            account_moves = self.env['account.move'].sudo().create(move_vals_list)
            account_moves._post()
        return res

    # -------------------------------------------------------------------------
    # Misc.
    # -------------------------------------------------------------------------
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self)._get_product_accounts()
        res = self._get_asset_accounts()
        accounts.update({
            'stock_input': res['stock_input'] or self.categ_id.property_stock_account_input_categ_id,
            'stock_output': res['stock_output'] or self.categ_id.property_stock_account_output_categ_id,
            'stock_valuation': self.categ_id.property_stock_valuation_account_id,
        })
        return accounts

    def get_product_accounts(self, fiscal_pos=None):
        """ Add the stock journal related to product to the result of super()
        @return: dictionary which contains all needed information regarding stock accounts and journal and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self).get_product_accounts(fiscal_pos=fiscal_pos)
        accounts.update({'stock_journal': self.categ_id.property_stock_journal or False})
        return accounts


class ProductProduct(models.Model):
    _inherit = 'product.product'

    value_svl = fields.Float(compute='_compute_value_svl', compute_sudo=True)
    quantity_svl = fields.Float(compute='_compute_value_svl', compute_sudo=True)
    avg_cost = fields.Monetary(string="Average Cost", compute='_compute_value_svl', compute_sudo=True, currency_field='company_currency_id')
    total_value = fields.Monetary(string="Total Value", compute='_compute_value_svl', compute_sudo=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one(
        'res.currency', 'Valuation Currency', compute='_compute_value_svl', compute_sudo=True,
        help="Technical field to correctly show the currently selected company's currency that corresponds "
             "to the totaled value of the product's valuation layers")
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'product_id')
    valuation = fields.Selection(related="categ_id.property_valuation", readonly=True)
    cost_method = fields.Selection(related="categ_id.property_cost_method", readonly=True)

    def write(self, vals):
        if 'standard_price' in vals and not self.env.context.get('disable_auto_svl'):
            self.filtered(lambda p: p.cost_method != 'fifo')._change_standard_price(vals['standard_price'])
        return super(ProductProduct, self).write(vals)

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company')
    def _compute_value_svl(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        domain = [
            *self._check_company_domain(company_id),
            ('product_id', 'in', self.ids),
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        groups = self.env['stock.valuation.layer']._read_group(
            domain,
            groupby=['product_id'],
            aggregates=['value:sum', 'quantity:sum'],
        )
        # Browse all products and compute products' quantities_dict in batch.
        group_mapping = {product: aggregates for product, *aggregates in groups}
        for product in self:
            value_sum, quantity_sum = group_mapping.get(product._origin, (0, 0))
            value_svl = company_id.currency_id.round(value_sum)
            avg_cost = value_svl / quantity_sum if quantity_sum else 0
            product.value_svl = value_svl
            product.quantity_svl = quantity_sum
            product.avg_cost = avg_cost
            product.total_value = avg_cost * product.sudo(False).qty_available

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_revaluation(self):
        self.ensure_one()
        ctx = dict(self._context, default_product_id=self.id, default_company_id=self.env.company.id)
        return {
            'name': _("Product Revaluation"),
            'view_mode': 'form',
            'res_model': 'stock.valuation.layer.revaluation',
            'view_id': self.env.ref('stock_account.stock_valuation_layer_revaluation_form_view').id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'target': 'new'
        }

    # -------------------------------------------------------------------------
    # SVL creation helpers
    # -------------------------------------------------------------------------
    def _prepare_in_svl_vals(self, quantity, unit_cost):
        """Prepare the values for a stock valuation layer created by a receipt.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :param unit_cost: the unit cost to value `quantity`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        value = company.currency_id.round(unit_cost * quantity)
        return {
            'product_id': self.id,
            'value': value,
            'unit_cost': unit_cost,
            'quantity': quantity,
            'remaining_qty': quantity,
            'remaining_value': value,
        }

    def _prepare_out_svl_vals(self, quantity, company):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        currency = company.currency_id
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals = {
            'product_id': self.id,
            'value': currency.round(quantity * self.standard_price),
            'unit_cost': self.standard_price,
            'quantity': quantity,
        }
        fifo_vals = self._run_fifo(abs(quantity), company)
        vals['remaining_qty'] = fifo_vals.get('remaining_qty')
        # In case of AVCO, fix rounding issue of standard price when needed.
        if self.product_tmpl_id.cost_method == 'average' and not float_is_zero(self.quantity_svl, precision_rounding=self.uom_id.rounding):
            rounding_error = currency.round(
                (self.standard_price * self.quantity_svl - self.value_svl) * abs(quantity / self.quantity_svl)
            )
            if rounding_error:
                # If it is bigger than the (smallest number of the currency * quantity) / 2,
                # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                if abs(rounding_error) <= max((abs(quantity) * currency.rounding) / 2, currency.rounding):
                    vals['value'] += rounding_error
                    vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                        '+' if rounding_error > 0 else '',
                        float_repr(rounding_error, precision_digits=currency.decimal_places),
                        currency.symbol
                    )
        if self.product_tmpl_id.cost_method == 'fifo':
            vals.update(fifo_vals)
        return vals

    def _change_standard_price(self, new_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        # Handle stock valuation layers.

        if self.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(_("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        company_id = self.env.company
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        rounded_new_price = float_round(new_price, precision_digits=price_unit_prec)
        for product in self:
            if product.cost_method not in ('standard', 'average'):
                continue
            quantity_svl = product.sudo().quantity_svl
            if float_compare(quantity_svl, 0.0, precision_rounding=product.uom_id.rounding) <= 0:
                continue
            value_svl = product.sudo().value_svl
            value = company_id.currency_id.round((rounded_new_price * quantity_svl) - value_svl)
            if company_id.currency_id.is_zero(value):
                continue

            svl_vals = {
                'company_id': company_id.id,
                'product_id': product.id,
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

        # Handle account moves.
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self}
        am_vals_list = []
        for stock_valuation_layer in stock_valuation_layers:
            product = stock_valuation_layer.product_id
            value = stock_valuation_layer.value

            if not product.is_storable or product.valuation != 'real_time':
                continue

            # Sanity check.
            if not product_accounts[product.id].get('expense'):
                raise UserError(_('You must set a counterpart account on your product category.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

            if value < 0:
                debit_account_id = product_accounts[product.id]['expense'].id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
            else:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['expense'].id

            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': company_id.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [stock_valuation_layer.id])],
                'move_type': 'entry',
                'line_ids': [(0, 0, {
                    'name': _(
                        '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
                        user=self.env.user.name,
                        previous=product.standard_price,
                        new_price=new_price,
                        product=product.display_name
                    ),
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': _(
                        '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
                        user=self.env.user.name,
                        previous=product.standard_price,
                        new_price=new_price,
                        product=product.display_name
                    ),
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                })],
            }
            am_vals_list.append(move_vals)

        account_moves = self.env['account.move'].sudo().create(am_vals_list)
        if account_moves:
            account_moves._post()

    def _get_fifo_candidates_domain(self, company):
        return [
            ("product_id", "=", self.id),
            ("remaining_qty", ">", 0),
            ("company_id", "=", company.id),
        ]

    def _get_fifo_candidates(self, company):
        candidates_domain = self._get_fifo_candidates_domain(company)
        return self.env["stock.valuation.layer"].sudo().search(candidates_domain)

    def _run_fifo(self, quantity, company):
        self.ensure_one()

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        candidates = self._get_fifo_candidates(company)
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        for candidate in candidates:
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

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

        for product in self:
            all_candidates = all_candidates_by_product[product.id]
            current_real_time_svls = ValuationLayer
            for svl_to_vacuum in svls_to_vacuum_by_product[product.id]:
                # We don't use search to avoid executing _flush_search and to decrease interaction with DB
                candidates = all_candidates.filtered(
                    lambda r: r.create_date > svl_to_vacuum.create_date
                    or r.create_date == svl_to_vacuum.create_date
                    and r.id > svl_to_vacuum.id
                )
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
                })
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
            if product.cost_method in ['average', 'fifo'] and not float_is_zero(product.quantity_svl,
                                                                      precision_rounding=product.uom_id.rounding):
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
            })
            vacuum_pairs_to_reconcile.append((vacuum_svl, svl_to_vacuum))
        new_account_moves = AccountMove.create(account_move_vals)
        new_account_moves._post()
        for new_account_move, (vacuum_svl, svl_to_vacuum) in zip(new_account_moves, vacuum_pairs_to_reconcile):
            account = svls_accounts[svl_to_vacuum.id]['stock_output']
            to_reconcile_account_move_lines = vacuum_svl.account_move_id.line_ids.filtered(lambda l: not l.reconciled and l.account_id == account and l.account_id.reconcile)
            to_reconcile_account_move_lines += new_account_move.line_ids.filtered(lambda l: not l.reconciled and l.account_id == account and l.account_id.reconcile)
            to_reconcile_account_move_lines.reconcile()

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
        for product in impacted_products:
            # FIXME sle: why not use products_orig_quantity_svl here?
            if float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                # FIXME: create an empty layer to track the change?
                continue
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
        for product in self:
            quantity_svl = products_orig_quantity_svl[product.id]
            if quantity_svl:
                if float_compare(quantity_svl, 0, precision_rounding=product.uom_id.rounding) > 0:
                    svl_vals = product._prepare_in_svl_vals(quantity_svl, product.standard_price)
                else:
                    svl_vals = product._prepare_out_svl_vals(abs(quantity_svl), self.env.company)
                svl_vals['description'] = description
                svl_vals['company_id'] = self.env.company.id
                refill_stock_svl_list.append(svl_vals)
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
        self.ensure_one()
        if not qty_to_invoice:
            return 0

        candidates = stock_moves\
            .sudo()\
            .filtered(lambda m: is_returned == bool(m.origin_returned_move_id and sum(m.stock_valuation_layer_ids.mapped('quantity')) >= 0))\
            .mapped('stock_valuation_layer_ids')

        if self.env.context.get('candidates_prefetch_ids'):
            candidates = candidates.with_prefetch(self.env.context.get('candidates_prefetch_ids'))

        if len(candidates) > 1:
            candidates = candidates.sorted(lambda svl: (svl.create_date, svl.id))

        value_invoiced = self.env.context.get('value_invoiced', 0)
        if 'value_invoiced' in self.env.context:
            qty_valued, valuation = candidates._consume_all(qty_invoiced, value_invoiced, qty_to_invoice)
        else:
            qty_valued, valuation = candidates._consume_specific_qty(qty_invoiced, qty_to_invoice)

        # If there's still quantity to invoice but we're out of candidates, we chose the standard
        # price to estimate the anglo saxon price unit.
        missing = qty_to_invoice - qty_valued
        for sml in stock_moves.move_line_ids:
            if not sml._should_exclude_for_valuation():
                continue
            missing -= sml.product_uom_id._compute_quantity(sml.quantity, self.uom_id, rounding_method='HALF-UP')
        if float_compare(missing, 0, precision_rounding=self.uom_id.rounding) > 0:
            valuation += self.standard_price * missing

        return valuation / qty_to_invoice


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_valuation = fields.Selection([
        ('manual_periodic', 'Manual'),
        ('real_time', 'Automated')], string='Inventory Valuation',
        company_dependent=True, copy=True, required=True,
        help="""Manual: The accounting entries to value the inventory are not posted automatically.
        Automated: An accounting entry is automatically created to value the inventory when a product enters or leaves the company.
        """)
    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)')], string="Costing Method",
        company_dependent=True, copy=True, required=True,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
        Average Cost (AVCO): The products are valued at weighted average cost.
        First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.
        """)
    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal', company_dependent=True,
        help="When doing automated inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed.")
    property_stock_account_input_categ_id = fields.Many2one(
        'account.account', 'Stock Input Account', company_dependent=True,
        domain="[('deprecated', '=', False)]", check_company=True,
        help="""Counterpart journal items for all incoming stock moves will be posted in this account, unless there is a specific valuation account
                set on the source location. This is the default value for all products in this category. It can also directly be set on each product.""")
    property_stock_account_output_categ_id = fields.Many2one(
        'account.account', 'Stock Output Account', company_dependent=True,
        domain="[('deprecated', '=', False)]", check_company=True,
        help="""When doing automated inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account,
                unless there is a specific valuation account set on the destination location. This is the default value for all products in this category.
                It can also directly be set on each product.""")
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account', company_dependent=True,
        domain="[('deprecated', '=', False)]", check_company=True,
        help="""When automated inventory valuation is enabled on a product, this account will hold the current value of the products.""",)

    @api.model
    def _get_stock_account_property_field_names(self):
        return [
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ]

    @api.constrains(lambda self: tuple(self._get_stock_account_property_field_names() + ['property_valuation']))
    def _check_valuation_accounts(self):
        fnames = self._get_stock_account_property_field_names()
        for category in self:
            # "compute" properties in constraint because ORM doesn't support computed properties
            for property_field in fnames:
                category[property_field] = category.property_valuation == 'real_time' and (
                    category[property_field]
                    or self.env['ir.property']._get(property_field, 'product.category')
                )

            # Prevent to set the valuation account as the input or output account.
            valuation_account = category.property_stock_valuation_account_id
            input_and_output_accounts = category.property_stock_account_input_categ_id | category.property_stock_account_output_categ_id
            if valuation_account and valuation_account in input_and_output_accounts:
                raise ValidationError(_('The Stock Input and/or Output accounts cannot be the same as the Stock Valuation account.'))

    @api.model
    def _create_default_stock_accounts_properties(self):
        IrProperty = self.env['ir.property']
        company = self.env.ref('base.main_company')
        output_field = self.env['ir.model.fields'].search([
            ('model', '=', 'product.category'),
            ('name', '=', 'property_stock_account_output_categ_id'),
        ])
        output_property = IrProperty.search([
            ('fields_id', '=', output_field.id),
            ('res_id', '=', False),
            ('company_id', '=', company.id),
        ])
        if not output_property:
            IrProperty._load_records([{
                'xml_id': 'stock_account.property_stock_account_output_categ_id',
                'noupdate': True,
                'values': {
                    'name': 'property_stock_account_output_categ_id',
                    'fields_id': output_field.id,
                    'value': False,
                    'company_id': company.id,
                },
            }])

        input_field = self.env['ir.model.fields'].search([
            ('model', '=', 'product.category'),
            ('name', '=', 'property_stock_account_input_categ_id'),
        ])
        input_property = IrProperty.search([
            ('fields_id', '=', input_field.id),
            ('res_id', '=', False),
            ('company_id', '=', company.id),
        ])
        if not input_property:
            IrProperty._load_records([{
                'xml_id': 'stock_account.property_stock_account_input_categ_id',
                'noupdate': True,
                'values': {
                    'name': 'property_stock_account_input_categ_id',
                    'fields_id': input_field.id,
                    'value': False,
                    'company_id': company.id,
                },
            }])

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        if self.parent_id and not self.product_count:
            self.property_cost_method = self.parent_id.property_cost_method

    @api.onchange('property_cost_method')
    def onchange_property_cost(self):
        if not self._origin:
            # don't display the warning when creating a product category
            return
        return {
            'warning': {
                'title': _("Warning"),
                'message': _("Changing your cost method is an important change that will impact your inventory valuation. Are you sure you want to make that change?"),
            }
        }

    def write(self, vals):
        impacted_categories = {}
        move_vals_list = []
        Product = self.env['product.product']
        SVL = self.env['stock.valuation.layer']

        if 'property_cost_method' in vals or 'property_valuation' in vals:
            # When the cost method or the valuation are changed on a product category, we empty
            # out and replenish the stock for each impacted products.
            new_cost_method = vals.get('property_cost_method')
            new_valuation = vals.get('property_valuation')

            for product_category in self:
                valuation_impacted = False
                if new_cost_method and new_cost_method != product_category.property_cost_method:
                    valuation_impacted = True
                if new_valuation and new_valuation != product_category.property_valuation:
                    valuation_impacted = True
                if valuation_impacted is False:
                    continue

                # Empty out the stock with the current cost method.
                if new_cost_method:
                    description = _(
                        "Costing method change for product category %(category)s: from %(old_method)s to %(new_method)s.",
                        category=product_category.display_name, old_method=product_category.property_cost_method, new_method=new_cost_method)
                else:
                    description = _(
                        "Valuation method change for product category %(category)s: from %(old_method)s to %(new_method)s.",
                        category=product_category.display_name, old_method=product_category.property_valuation, new_method=new_valuation)
                out_svl_vals_list, products_orig_quantity_svl, products = Product\
                    ._svl_empty_stock(description, product_category=product_category)
                out_stock_valuation_layers = SVL.sudo().create(out_svl_vals_list)
                if product_category.property_valuation == 'real_time':
                    move_vals_list += Product._svl_empty_stock_am(out_stock_valuation_layers)
                impacted_categories[product_category] = (products, description, products_orig_quantity_svl)

        res = super(ProductCategory, self).write(vals)

        for product_category, (products, description, products_orig_quantity_svl) in impacted_categories.items():
            # Replenish the stock with the new cost method.
            in_svl_vals_list = products._svl_replenish_stock(description, products_orig_quantity_svl)
            in_stock_valuation_layers = SVL.sudo().create(in_svl_vals_list)
            if product_category.property_valuation == 'real_time':
                move_vals_list += Product._svl_replenish_stock_am(in_stock_valuation_layers)

        # Check access right
        if move_vals_list and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(_("The action leads to the creation of a journal entry, for which you don't have the access rights."))
        # Create the account moves.
        if move_vals_list:
            account_moves = self.env['account.move'].sudo().create(move_vals_list)
            account_moves._post()
        return res
