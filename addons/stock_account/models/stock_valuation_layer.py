# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.tools import float_compare, float_is_zero


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
    unit_cost = fields.Float('Unit Value', digits='Product Price', readonly=True, group_operator=None)
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
    qty_valued_already_out = fields.Float(default=0) # Only for child layers
    qty_valued_in_stock = fields.Float(default=0) # Only for child layers
    qty_to_value_in_stock = fields.Float(compute='_compute_qty_to_value') # Only for parent layers
    qty_to_value_already_out = fields.Float(compute='_compute_qty_to_value') # Only for parent layers
    qty_overvalued = fields.Float(compute='_compute_qty_to_value') # Only for parent layers
    is_dummy = fields.Boolean(default=False)

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
            # Eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
            if svl.company_id.anglo_saxon_accounting:
                svl.stock_move_id._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=svl.product_id)

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

    @api.depends('quantity', 'remaining_qty',
                 'stock_valuation_layer_ids.qty_valued_already_out',
                 'stock_valuation_layer_ids.qty_valued_in_stock',
                 'stock_move_id.returned_move_ids.stock_valuation_layer_ids.quantity')
    def _compute_qty_to_value(self):
        """
        qty_to_value_in_stock: quantity pending definitive valuation that is still in stock
        qty_to_value_already_out: quantity pending definitive valuation that has already moved out-of-stock
        qty_overvalued: excess quantity valued due to some return of stock to vendor after definitively valuing it

        !!! Returns linked to the move are taken into account.
            If the move for this SVL has a (partial) return, then the returned qty is not included in the qty_to_value.
            Example: 10 items, return 3, then the total qty_to_value on the original SVL is 7.
        """
        for svl in self:
            # The total quantity that is returned in the move chain (as negative value, ex. 3 returned -> -3)
            return_qty = sum(svl.stock_move_id.returned_move_ids.stock_valuation_layer_ids.filtered(lambda move: move.quantity < 0).mapped('quantity'))
            real_qty = svl.quantity + return_qty
            qty_already_out = real_qty - svl.remaining_qty
            to_value_in = svl.remaining_qty - sum(svl.stock_valuation_layer_ids.mapped('qty_valued_in_stock'))
            to_value_out = qty_already_out - sum(svl.stock_valuation_layer_ids.mapped('qty_valued_already_out'))
            to_value_total = to_value_in + to_value_out

            # First, we check if this layer is overvalued (due to a vendor return) and compensate
            qty_overvalued = 0
            if float_compare(to_value_total, 0, precision_rounding=self.product_id.uom_id.rounding) < 0:
                qty_overvalued = -to_value_total
                to_value_in = 0
                to_value_out = 0

            # Some might have shipped out in the meanwhile
            if float_compare(to_value_in, 0, precision_rounding=self.product_id.uom_id.rounding) < 0:
                to_value_out += to_value_in
                to_value_in = 0

            svl.qty_to_value_in_stock = to_value_in
            svl.qty_to_value_already_out = to_value_out
            svl.qty_overvalued = qty_overvalued

    def calculate_refund_quantities(self, qty_to_refund):
        """
            Calculate the different quantities to refund from this correction svl,
            refunding only maximally the remaining_qty provided.
            :param remaining_qty:  The (maximal) amount to refund from the original bill.
            :return:               A tuple containing the different refund quantities to take:
                                   overvalued qty, in stock qty, meanwhile out qty, already out qty
        """
        parent_layer = self.stock_valuation_layer_id

        # 1. Calculate the quantity that was in stock when posting but has been returned to the vendor
        common_overvalued = min(qty_to_refund, parent_layer.qty_overvalued)
        qty_to_refund -= common_overvalued

        # 2. Calculate the quantity that was in stock when posting and still is in stock
        meanwhile_out_qty = max(self.qty_valued_in_stock - parent_layer.remaining_qty, 0)
        amount_still_in = self.qty_valued_in_stock - meanwhile_out_qty
        common_still_in_qty = min(qty_to_refund, amount_still_in)
        qty_to_refund -= common_still_in_qty

        # 3. Calculate the quantity that was in stock when posting but went out in the meanwhile
        common_meanwhile_out_qty = min(qty_to_refund, meanwhile_out_qty)
        qty_to_refund -= common_meanwhile_out_qty
        self.qty_valued_in_stock -= common_meanwhile_out_qty
        self.qty_valued_already_out += common_meanwhile_out_qty

        # 4. Calculate the quantity that was already out when posting the original invoice
        common_out_qty = min(qty_to_refund, self.qty_valued_already_out)
        qty_to_refund -= common_out_qty

        return common_overvalued, common_still_in_qty, common_meanwhile_out_qty, common_out_qty
