# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('workorder_id')
    def _compute_manual_consumption(self):
        super()._compute_manual_consumption()
        for move in self:
            if move.product_id in move.workorder_id.check_ids.component_id:
                move.manual_consumption = True

    def _should_bypass_set_qty_producing(self):
        production = self.raw_material_production_id or self.production_id
        if production and ((self.product_id in production.workorder_ids.quality_point_ids.component_id) or self.operation_id):
            return True
        return super()._should_bypass_set_qty_producing()

    def _action_assign(self, force_qty=False):
        res = super()._action_assign(force_qty=force_qty)
        for workorder in self.raw_material_production_id.workorder_ids:
            for check in workorder.check_ids:
                if check.test_type not in ('register_consumed_materials', 'register_byproducts'):
                    continue
                if check.move_line_id:
                    continue
                check.write(workorder._defaults_from_move(check.move_id))
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_quality_check(self):
        self.env['quality.check'].search([('move_id', 'in', self.ids)]).unlink()

    def _is_manual_consumption(self):
        # Mark a move as manual if linked to a quality check.
        is_linked_to_quality_check = any(qc.test_type == 'register_consumed_materials' for qc in self.move_line_ids.quality_check_ids)
        return super()._is_manual_consumption() or is_linked_to_quality_check

    def action_add_from_catalog_raw(self):
        mo = self.env['mrp.production'].browse(self.env.context.get('order_id'))
        return mo.with_context(child_field='move_raw_ids', from_shop_floor=self.env.context.get('from_shop_floor')).action_add_from_catalog()
