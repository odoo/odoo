# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, models, fields
from odoo.tools.float_utils import float_is_zero, float_round
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super(StockMove, self)._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if self.purchase_line_id:
            vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _get_price_unit(self):
        if self.product_id == self.purchase_line_id.product_id or not self.bom_line_id or self._should_ignore_pol_price():
            return super()._get_price_unit()
        line = self.purchase_line_id
        # price_unit here with uom of product
        kit_price_unit = line._get_gross_price_unit()
        bom_line = self.bom_line_id
        bom = bom_line.bom_id
        if line.currency_id != self.company_id.currency_id:
            kit_price_unit = line.currency_id._convert(kit_price_unit, self.company_id.currency_id, self.company_id, fields.Date.context_today(self), round=False)
        cost_share = self.cost_share / 100
        uom_factor = 1.0
        kit_product = bom.product_id or bom.product_tmpl_id

        # Convert uom from product_uom to bom_uom for kit product
        uom_factor = bom.product_uom_id._compute_quantity(uom_factor, kit_product.uom_id)

        # Convert uom from bom_line_uom to product_uom for bom_line
        uom_factor = bom_line.product_id.uom_id._compute_quantity(uom_factor, bom_line.product_uom_id)

        price_unit = kit_price_unit * cost_share * uom_factor * bom.product_qty / bom_line.product_qty
        if self.product_id.lot_valuated:
            return {lot: price_unit for lot in self.lot_ids}
        else:
            return {self.env['stock.lot']: price_unit}

    def _get_valuation_price_and_qty(self, related_aml, to_curr):
        valuation_price_unit_total, valuation_total_qty = super()._get_valuation_price_and_qty(related_aml, to_curr)
        boms = self.env['mrp.bom']._bom_find(related_aml.product_id, company_id=related_aml.company_id.id, bom_type='phantom')
        if related_aml.product_id in boms:
            kit_bom = boms[related_aml.product_id]
            order_qty = related_aml.product_id.uom_id._compute_quantity(related_aml.quantity, kit_bom.product_uom_id)
            filters = {
                'incoming_moves': lambda m: m.location_id.usage == 'supplier' and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                'outgoing_moves': lambda m: m.location_id.usage != 'supplier' and m.to_refund
            }
            valuation_total_qty = self._compute_kit_quantities(related_aml.product_id, order_qty, kit_bom, filters)
            valuation_total_qty = kit_bom.product_uom_id._compute_quantity(valuation_total_qty, related_aml.product_id.uom_id)
            if float_is_zero(valuation_total_qty, precision_rounding=related_aml.product_uom_id.rounding or related_aml.product_id.uom_id.rounding):
                raise UserError(_('Odoo is not able to generate the anglo saxon entries. The total valuation of %s is zero.', related_aml.product_id.display_name))
        return valuation_price_unit_total, valuation_total_qty

    def _get_qty_received_without_self(self):
        line = self.purchase_line_id
        if line and line.qty_received_method == 'stock_moves' and line.state != 'cancel' and any(move.product_id != line.product_id for move in line.move_ids):
            kit_bom = self.env['mrp.bom']._bom_find(line.product_id, company_id=line.company_id.id, bom_type='phantom').get(line.product_id)
            if kit_bom:
                return line._compute_kit_quantities_from_moves(line.move_ids - self, kit_bom)
        return super()._get_qty_received_without_self()

    @api.model
    def _round_in_svl_value(self, svl_vals_list):
        moves = self.env['stock.move'].browse({val['stock_move_id'] for val in svl_vals_list})
        move_kit_pol_mapping = {move.id: move.purchase_line_id for move in moves if move.purchase_line_id and move.purchase_line_id.product_id != move.product_id}
        if not move_kit_pol_mapping:
            return svl_vals_list
        vals_per_kit_line = defaultdict(list)
        for val in svl_vals_list:
            if pol := move_kit_pol_mapping.get(val['stock_move_id']):
                vals_per_kit_line[pol].append(val)
        company_id = self.env.context.get('force_company', self.env.company.id)
        currency = self.env['res.company'].browse(company_id).currency_id
        for vals in vals_per_kit_line.values():
            total_value = sum(val['unit_cost'] * val['quantity'] for val in vals)
            total_rounded_value = sum(val['value'] for val in vals)
            total_rounding_error = currency.round(total_value - total_rounded_value)
            nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
            rounding_error = float_round(nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0, precision_rounding=currency.rounding)
            for val in vals[:nber_rounding_steps]:
                val['value'] = currency.round(val['value'] + rounding_error)
                val['remaining_value'] = val['value']
        return svl_vals_list
