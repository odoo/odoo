# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.tools import float_compare, float_is_zero


class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _name = 'stock.valuation.layer'
    _description = 'Stock Valuation Layer'
    _order = 'create_date, id'

    _rec_name = 'product_id'

    company_id = fields.Many2one('res.company', 'Company', readonly=True, required=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True, required=True, check_company=True, auto_join=True)
    categ_id = fields.Many2one('product.category', related='product_id.categ_id')
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    quantity = fields.Float('Quantity', help='Quantity', readonly=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one(related='product_id.uom_id', readonly=True, required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id', readonly=True, required=True)
    unit_cost = fields.Monetary('Unit Value', readonly=True)
    value = fields.Monetary('Total Value', readonly=True)
    remaining_qty = fields.Float(readonly=True, digits='Product Unit of Measure')
    remaining_value = fields.Monetary('Remaining Value', readonly=True)
    description = fields.Char('Description', readonly=True)
    stock_valuation_layer_id = fields.Many2one('stock.valuation.layer', 'Linked To', readonly=True, check_company=True, index=True)
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'stock_valuation_layer_id')
    stock_move_id = fields.Many2one('stock.move', 'Stock Move', readonly=True, check_company=True, index=True)
    account_move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True, check_company=True, index=True)

    def init(self):
        tools.create_index(
            self._cr, 'stock_valuation_layer_index',
            self._table, ['product_id', 'remaining_qty', 'stock_move_id', 'company_id', 'create_date']
        )

    def _validate_accounting_entries(self):
        am_vals = []
        for svl in self:
            if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            am_vals += svl.stock_move_id.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
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
            returned_qty = sum([sm.product_uom._compute_quantity(sm.quantity_done, self.uom_id)
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
            returned_qty = sum([sm.product_uom._compute_quantity(sm.quantity_done, self.uom_id)
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
