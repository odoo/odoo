# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, models
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('bom_line_id')
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            if move.bom_line_id and move.bom_line_id.bom_id.type == 'phantom':
                move.packaging_uom_id = move.uom_id

    def _get_cost_ratio(self, quantity):
        self.ensure_one()
        if self.bom_line_id.bom_id.type == "phantom":
            uom_quantity = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
            if not self.uom_id.is_zero(uom_quantity):
                unit_kit_purchase = 1
                if self.purchase_line_id:
                    active_moves = self.purchase_line_id.move_ids.filtered(lambda m:
                        m.state != 'cancel'
                        and m.product_id == self.product_id
                        and m.picking_id != self.picking_id
                        and m.bom_line_id == self.bom_line_id
                        and float_compare(m.cost_share, self.cost_share, precision_digits=6) == 0
                    )
                    active_quantity = quantity + sum(active_moves.mapped('quantity'))
                    if active_quantity:
                        unit_kit_purchase = (quantity / active_quantity) * self.purchase_line_id.product_qty
                return (self.cost_share / 100) * (quantity / uom_quantity) * unit_kit_purchase
        return super()._get_cost_ratio(quantity)

    def _get_value_from_bill(self, aml):
        value = super()._get_value_from_bill(aml)
        if self.bom_line_id.bom_id.type == "phantom":
            value *= (self.cost_share / 100)
        return value

    def _get_quantity_from_bill(self, aml, quantity):
        self.ensure_one()
        if self.bom_line_id.bom_id.type == "phantom":
            return aml.product_uom_id._compute_quantity(quantity, self.product_id.uom_id)
        return super()._get_quantity_from_bill(aml, quantity)

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super()._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if self.purchase_line_id:
            vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

    def _merge_moves_fields(self):
        res = super()._merge_moves_fields()
        if not self.env.context.get('merge_extra'):
            res['cost_share'] = sum(self.mapped('cost_share'))
        return res

    def _get_qty_received_without_self(self):
        line = self.purchase_line_id
        if line and line.qty_received_method == 'stock_moves' and line.state != 'cancel' and any(move.product_id != line.product_id for move in line.move_ids):
            kit_bom = self.env['mrp.bom']._bom_find(line.product_id, company_id=line.company_id.id, bom_type='phantom').get(line.product_id)
            if kit_bom:
                return line._compute_kit_quantities_from_moves(line.move_ids - self, kit_bom)
        return super()._get_qty_received_without_self()

    def _get_upstream_documents_and_responsibles(self, visited):
        docs = super()._get_upstream_documents_and_responsibles(visited)
        for po_line in self.created_purchase_line_ids:
            if po_line.state not in ('done', 'cancel'):
                docs.extend(po_line._get_upstream_documents_and_responsibles(visited))
        return docs

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        for move in self.filtered(lambda m: m.raw_material_production_id):
            purchase_moves = move.move_orig_ids.filtered(lambda m: m.purchase_line_id)
            if purchase_moves:
                move.move_orig_ids = [Command.unlink(m.id) for m in purchase_moves]
            purchase_lines = (move | move.move_orig_ids).created_purchase_line_ids
            for po_line in purchase_lines:
                po = po_line.order_id
                documents = {(po, po.user_id): [({po_line: (move, (move.product_uom_qty, 0))}, [])]}
                move.raw_material_production_id.with_context(is_child_mo_unlink=True)._log_manufacture_exception(documents)
        return super()._unlink_if_draft_or_cancel()
