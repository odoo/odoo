# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import _, models
from odoo.tools.float_utils import float_is_zero
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
        kit_price_unit = line._get_gross_price_unit()
        cost_share = self.bom_line_id._get_cost_share()
        return kit_price_unit * cost_share

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
                raise UserError(_('Odoo is not able to generate the anglo saxon entries. The total valuation of %s is zero.') % related_aml.product_id.display_name)
        return valuation_price_unit_total, valuation_total_qty
