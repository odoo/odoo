# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Order Line',
        ondelete='set null', index='btree_not_null', readonly=True)
    created_purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Created Purchase Order Line',
        ondelete='set null', readonly=True, copy=False)

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields += ['purchase_line_id', 'created_purchase_line_id']
        return distinct_fields

    @api.model
    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return super()._prepare_merge_negative_moves_excluded_distinct_fields() + ['created_purchase_line_id']

    def _get_in_svl_vals(self, forced_quantity):
        svl_vals_list = []
        # Before define the incoming SVL values, checks if some quantities has
        # already been invoiced and still waiting to be receive.
        # In such case, get back the price from these waiting invoice lines.
        remainging_moves = self.env['stock.move']
        for move in self:
            product = move.product_id
            # Take invoice lines about the current product and who have waiting quantities.
            invoice_lines = move.purchase_line_id.invoice_lines.filtered(lambda l: l.product_id == product and l.qty_waiting_for_receipt > 0)
            if not invoice_lines:
                remainging_moves |= move
                continue
            quantity_received = 0
            # Gets values for each of those invoice lines.
            # TODO: checks what happens when receive less qty than already invoiced.
            for line in invoice_lines:
                same_uom = move.product_uom == line.product_uom_id
                line_qty = line.qty_waiting_for_receipt
                unit_cost = line.price_unit
                if not same_uom:
                    line_qty = line.product_uom_id._compute_quantity(line.qty_waiting_for_receipt, move.product_uom)
                    unit_cost = line.product_uom_id._compute_price(line.price_unit, move.product_uom)
                qty_to_process = min(move.quantity_done, line_qty)
                quantity_received += qty_to_process

                if same_uom:
                    line.qty_waiting_for_receipt -= qty_to_process
                else:  # Not the same UoM: reconverts the qty before decreases invoice wainting qty.
                    line.qty_waiting_for_receipt -= move.product_uom._compute_quantity(qty_to_process, line.product_uom_id)

                svl_vals = super(StockMove, move)._get_in_svl_vals(qty_to_process)
                svl_vals[0]['unit_cost'] = unit_cost
                svl_vals[0]['value'] = qty_to_process * unit_cost
                svl_vals[0]['description'] = move.picking_id.name
                svl_vals_list += svl_vals
                # If product cost method is AVCO, updates the standard price.
                # if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                if product.cost_method == 'average':
                    # TODO: checks with differents UoM for the move line and the invoice line.
                    unit_price_diff = unit_cost - product.standard_price
                    svl_qty = svl_vals[0]['quantity']
                    qty_delta = 1
                    if product.qty_available > 0:
                        qty_delta = svl_qty / (svl_qty + product.quantity_svl)
                    standard_price_diff = unit_price_diff * qty_delta
                    product.with_company(self.company_id).sudo().with_context(disable_auto_svl=True).standard_price += standard_price_diff
            # If it remains quantities to process after processed the waiting
            # ones, gets SVL values for the remaining quantity.
            if quantity_received < move.quantity_done:
                qty_to_process = move.quantity_done - quantity_received
                svl_vals = super(StockMove, move)._get_in_svl_vals(qty_to_process)
                svl_vals[0]['description'] = move.picking_id.name
                svl_vals_list += svl_vals
        return svl_vals_list + super(StockMove, remainging_moves)._get_in_svl_vals(forced_quantity)

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            if line.taxes_id:
                qty = line.product_qty or 1
                price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=qty)['total_void']
                price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                # The date must be today, and not the date of the move since the move move is still
                # in assigned state. However, the move date is the scheduled date until move is
                # done, then date of actual move processing. See:
                # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self), round=False)
            return price_unit
        return super(StockMove, self)._get_price_unit()

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description):
        """ Overridden from stock_account to support amount_currency on valuation lines generated from po
        """
        self.ensure_one()

        rslt = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description)
        if self.purchase_line_id:
            purchase_currency = self.purchase_line_id.currency_id
            if purchase_currency != self.company_id.currency_id:
                # Do not use price_unit since we want the price tax excluded. And by the way, qty
                # is in the UOM of the product, not the UOM of the PO line.
                purchase_price_unit = (
                    self.purchase_line_id.price_subtotal / self.purchase_line_id.product_uom_qty
                    if self.purchase_line_id.product_uom_qty
                    else self.purchase_line_id.price_unit
                )
                currency_move_valuation = purchase_currency.round(purchase_price_unit * abs(qty))
                rslt['credit_line_vals']['amount_currency'] = rslt['credit_line_vals']['credit'] and -currency_move_valuation or currency_move_valuation
                rslt['credit_line_vals']['currency_id'] = purchase_currency.id
                rslt['debit_line_vals']['amount_currency'] = rslt['debit_line_vals']['credit'] and -currency_move_valuation or currency_move_valuation
                rslt['debit_line_vals']['currency_id'] = purchase_currency.id
        return rslt

    def _prepare_extra_move_vals(self, qty):
        vals = super(StockMove, self)._prepare_extra_move_vals(qty)
        vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _prepare_move_split_vals(self, uom_qty):
        vals = super(StockMove, self)._prepare_move_split_vals(uom_qty)
        vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _prepare_procurement_values(self):
        proc_values = super()._prepare_procurement_values()
        if self.restrict_partner_id:
            proc_values['supplierinfo_name'] = self.restrict_partner_id
            self.restrict_partner_id = False
        return proc_values

    def _clean_merged(self):
        super(StockMove, self)._clean_merged()
        self.write({'created_purchase_line_id': False})

    def _get_upstream_documents_and_responsibles(self, visited):
        if self.created_purchase_line_id and self.created_purchase_line_id.state not in ('done', 'cancel') \
                and (self.created_purchase_line_id.state != 'draft' or self._context.get('include_draft_documents')):
            return [(self.created_purchase_line_id.order_id, self.created_purchase_line_id.order_id.user_id, visited)]
        elif self.purchase_line_id and self.purchase_line_id.state not in ('done', 'cancel'):
            return[(self.purchase_line_id.order_id, self.purchase_line_id.order_id.user_id, visited)]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)

    def _get_related_invoices(self):
        """ Overridden to return the vendor bills related to this stock move.
        """
        rslt = super(StockMove, self)._get_related_invoices()
        rslt += self.mapped('picking_id.purchase_id.invoice_ids').filtered(lambda x: x.state == 'posted')
        return rslt

    def _get_source_document(self):
        res = super()._get_source_document()
        return self.purchase_line_id.order_id or res

    def _get_valuation_price_and_qty(self, related_aml, to_curr):
        valuation_price_unit_total = 0
        valuation_total_qty = 0
        for val_stock_move in self:
            # In case val_stock_move is a return move, its valuation entries have been made with the
            # currency rate corresponding to the original stock move
            valuation_date = val_stock_move.origin_returned_move_id.date or val_stock_move.date
            svl = val_stock_move.with_context(active_test=False).mapped('stock_valuation_layer_ids').filtered(
                lambda l: l.quantity)
            layers_qty = sum(svl.mapped('quantity'))
            layers_values = sum(svl.mapped('value'))
            valuation_price_unit_total += related_aml.company_currency_id._convert(
                layers_values, to_curr, related_aml.company_id, valuation_date, round=False,
            )
            valuation_total_qty += layers_qty
        if float_is_zero(valuation_total_qty, precision_rounding=related_aml.product_uom_id.rounding or related_aml.product_id.uom_id.rounding):
            raise UserError(
                _('Odoo is not able to generate the anglo saxon entries. The total valuation of %s is zero.') % related_aml.product_id.display_name)
        return valuation_price_unit_total, valuation_total_qty
