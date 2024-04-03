# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _compute_is_dropship(self):
        dropship_subcontract_pickings = self.filtered(lambda p:
            p.location_id.usage == 'supplier'
            and any(m.location_dest_id == m.partner_id.property_stock_subcontractor
                    or (m.partner_id.property_stock_subcontractor.parent_path
                        and m.location_dest_id.parent_path
                        and m.partner_id.property_stock_subcontractor.parent_path in m.location_dest_id.parent_path)
                    for m in p.move_lines)
        )
        dropship_subcontract_pickings.is_dropship = True
        super(StockPicking, self - dropship_subcontract_pickings)._compute_is_dropship()

    def _get_warehouse(self, subcontract_move):
        if subcontract_move.sale_line_id:
            return subcontract_move.sale_line_id.order_id.warehouse_id
        return super(StockPicking, self)._get_warehouse(subcontract_move)

    def _action_done(self):
        res = super()._action_done()
        # If needed, create a compensation layer, so we add the MO cost to the dropship one
        svls = self.env['stock.valuation.layer']
        for move in self.move_lines:
            if not (move.is_subcontract and move._is_dropshipped() and move.state == 'done'):
                continue

            dropship_svls = move.stock_valuation_layer_ids
            if not dropship_svls:
                continue

            subcontract_svls = move.move_orig_ids.stock_valuation_layer_ids
            subcontract_value = sum(subcontract_svls.mapped('value'))
            dropship_value = abs(sum(dropship_svls.mapped('value')))
            diff = subcontract_value - dropship_value
            if float_compare(diff, 0, precision_rounding=move.company_id.currency_id.rounding) <= 0:
                continue

            svl_vals = move._prepare_common_svl_vals()
            svl_vals.update({
                'remaining_value': 0,
                'remaining_qty': 0,
                'value': -diff,
                'quantity': 0,
                'unit_cost': 0,
                'stock_valuation_layer_id': dropship_svls[0].id,
                'stock_move_id': move.id,
            })
            svls |= self.env['stock.valuation.layer'].create(svl_vals)
        svls._validate_accounting_entries()

        return res

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        res = super()._prepare_subcontract_mo_vals(subcontract_move, bom)
        if not res.get('picking_type_id') and (
                subcontract_move.location_dest_id.usage == 'customer'
                or subcontract_move.partner_id.property_stock_subcontractor.parent_path in subcontract_move.location_dest_id.parent_path
        ):
            # If the if-condition is respected, it means that `subcontract_move` is not
            # related to a specific warehouse. This can happen if, for instance, the user
            # confirms a PO with a subcontracted product that should be delivered to a
            # customer (dropshipping). In that case, we can use a default warehouse to
            # get the picking type
            default_warehouse = self.env['stock.warehouse'].search([('company_id', '=', subcontract_move.company_id.id)], limit=1)
            res['picking_type_id'] = default_warehouse.subcontracting_type_id.id,
        return res
