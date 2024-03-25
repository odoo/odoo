# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

from collections import defaultdict


class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _name = 'stock.valuation.layer'
    _description = 'Stock Valuation Layer'
    _order = 'create_date, id'

    _rec_name = 'product_id'

    company_id = fields.Many2one('res.company', 'Company', readonly=True, required=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True, required=True, check_company=True, auto_join=True)
    categ_id = fields.Many2one('product.category', related='product_id.categ_id', store=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    quantity = fields.Float('Quantity', readonly=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one(related='product_id.uom_id', readonly=True, required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id', readonly=True, required=True)
    unit_cost = fields.Float('Unit Value', digits='Product Price', readonly=True, aggregator=None)
    value = fields.Monetary('Total Value', readonly=True)
    remaining_qty = fields.Float(readonly=True, digits='Product Unit of Measure')
    remaining_value = fields.Monetary('Remaining Value', readonly=True)
    description = fields.Char('Description', readonly=True)
    stock_valuation_layer_id = fields.Many2one('stock.valuation.layer', 'Linked To', readonly=True, check_company=True, index=True)
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'stock_valuation_layer_id')
    stock_move_id = fields.Many2one('stock.move', 'Stock Move', readonly=True, check_company=True, index=True)
    account_move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True, check_company=True, index="btree_not_null")
    account_move_line_id = fields.Many2one('account.move.line', 'Invoice Line', readonly=True, check_company=True, index="btree_not_null")
    reference = fields.Char(related='stock_move_id.reference')
    price_diff_value = fields.Float('Invoice value correction with invoice currency')
    warehouse_id = fields.Many2one('stock.warehouse', string="Receipt WH", compute='_compute_warehouse_id', search='_search_warehouse_id')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number', check_company=True, index=True)

    def init(self):
        tools.create_index(
            self._cr, 'stock_valuation_layer_index',
            self._table, ['product_id', 'remaining_qty', 'stock_move_id', 'company_id', 'create_date']
        )

    def _compute_warehouse_id(self):
        for svl in self:
            if svl.stock_move_id.location_id.usage == "internal":
                svl.warehouse_id = svl.stock_move_id.location_id.warehouse_id.id
            else:
                svl.warehouse_id = svl.stock_move_id.location_dest_id.warehouse_id.id

    def _search_warehouse_id(self, operator, value):
        layer_ids = self.search([
            '|',
            ('stock_move_id.location_dest_id.warehouse_id', operator, value),
            '&',
            ('stock_move_id.location_id.usage', '=', 'internal'),
            ('stock_move_id.location_id.warehouse_id', operator, value),
        ]).ids
        return [('id', 'in', layer_ids)]

    def _validate_accounting_entries(self):
        am_vals = []
        aml_to_reconcile = defaultdict(set)
        for svl in self:
            if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            move = svl.stock_move_id
            if not move:
                move = svl.stock_valuation_layer_id.stock_move_id
            am_vals += move.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
        if am_vals:
            account_moves = self.env['account.move'].sudo().create(am_vals)
            account_moves._post()
        for svl in self:
            move = svl.stock_move_id
            product = svl.product_id
            if svl.company_id.anglo_saxon_accounting:
                move._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=product)
            for aml in (move | move.origin_returned_move_id)._get_all_related_aml():
                if aml.reconciled or aml.move_id.state != "posted" or not aml.account_id.reconcile:
                    continue
                aml_to_reconcile[(product, aml.account_id)].add(aml.id)
        for aml_ids in aml_to_reconcile.values():
            self.env['account.move.line'].browse(aml_ids).reconcile()

    def _validate_analytic_accounting_entries(self):
        for svl in self:
            svl.stock_move_id._account_analytic_entry_move()

    def action_open_journal_entry(self):
        self.ensure_one()
        if not self.account_move_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.account_move_id.id
        }

    def action_valuation_at_date(self):
        #  Handler called when the user clicked on the 'Valuation at Date' button.
        #  Opens wizard to display, at choice, the products inventory or a computed
        #  inventory at a given date.
        context = {}
        if ("default_product_id" in self.env.context):
            context["product_id"] = self.env.context["default_product_id"]
        elif ("default_product_tmpl_id" in self.env.context):
            context["product_tmpl_id"] = self.env.context["default_product_tmpl_id"]

        return {
            "res_model": "stock.quantity.history",
            "views": [[False, "form"]],
            "target": "new",
            "type": "ir.actions.act_window",
            "context": context,
        }

    def action_open_reference(self):
        self.ensure_one()
        if self.stock_move_id:
            action = self.stock_move_id.action_open_reference()
            if action['res_model'] != 'stock.move':
                return action
        return {
            'res_model': self._name,
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'res_id': self.id,
        }

    def _consume_specific_qty(self, qty_valued, qty_to_value):
        """
        Iterate on the SVL to first skip the qty already valued. Then, keep
        iterating to consume `qty_to_value` and stop
        The method returns the valued quantity and its valuation
        """
        if not self:
            return 0, 0

        rounding = self.product_id.uom_id.rounding
        qty_to_take_on_candidates = qty_to_value
        tmp_value = 0  # to accumulate the value taken on the candidates
        for candidate in self:
            if float_is_zero(candidate.quantity, precision_rounding=rounding):
                continue
            candidate_quantity = abs(candidate.quantity)
            returned_qty = sum([sm.product_uom._compute_quantity(sm.quantity, self.uom_id)
                                for sm in candidate.stock_move_id.returned_move_ids if sm.state == 'done'])
            candidate_quantity -= returned_qty
            if float_is_zero(candidate_quantity, precision_rounding=rounding):
                continue
            if not float_is_zero(qty_valued, precision_rounding=rounding):
                qty_ignored = min(qty_valued, candidate_quantity)
                qty_valued -= qty_ignored
                candidate_quantity -= qty_ignored
                if float_is_zero(candidate_quantity, precision_rounding=rounding):
                    continue
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate_quantity)

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += qty_taken_on_candidate * ((candidate.value + sum(candidate.stock_valuation_layer_ids.mapped('value'))) / candidate.quantity)
            if float_is_zero(qty_to_take_on_candidates, precision_rounding=rounding):
                break

        return qty_to_value - qty_to_take_on_candidates, tmp_value

    def _consume_all(self, qty_valued, valued, qty_to_value):
        """
        The method consumes all svl to get the total qty/value. Then it deducts
        the already consumed qty/value. Finally, it tries to consume the `qty_to_value`
        The method returns the valued quantity and its valuation
        """
        if not self:
            return 0, 0

        rounding = self.product_id.uom_id.rounding
        qty_total = -qty_valued
        value_total = -valued
        new_valued_qty = 0
        new_valuation = 0

        for svl in self:
            if float_is_zero(svl.quantity, precision_rounding=rounding):
                continue
            relevant_qty = abs(svl.quantity)
            returned_qty = sum([sm.product_uom._compute_quantity(sm.quantity, self.uom_id)
                                for sm in svl.stock_move_id.returned_move_ids if sm.state == 'done'])
            relevant_qty -= returned_qty
            if float_is_zero(relevant_qty, precision_rounding=rounding):
                continue
            qty_total += relevant_qty
            value_total += relevant_qty * ((svl.value + sum(svl.stock_valuation_layer_ids.mapped('value'))) / svl.quantity)

        if float_compare(qty_total, 0, precision_rounding=rounding) > 0:
            unit_cost = value_total / qty_total
            new_valued_qty = min(qty_total, qty_to_value)
            new_valuation = unit_cost * new_valued_qty

        return new_valued_qty, new_valuation

    def _change_standart_price_accounting_entries(self, new_price):
        # Handle account moves.
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self.product_id}
        company_id = self.env.company
        am_vals_list = []
        for layer in self:
            product = layer.product_id
            value = layer.value

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

            name = _(
                '%(user)s changed cost from %(previous)s to %(new_price)s - %(record)s',
                user=self.env.user.name,
                previous=layer.lot_id.standard_price if layer.lot_id else product.standard_price,
                new_price=new_price,
                record=layer.lot_id.display_name or product.display_name
            )
            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': company_id.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [layer.id])],
                'move_type': 'entry',
                'line_ids': [(0, 0, {
                    'name': name,
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': name,
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
