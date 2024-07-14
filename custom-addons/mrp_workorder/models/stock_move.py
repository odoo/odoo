# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _should_bypass_set_qty_producing(self):
        production = self.raw_material_production_id or self.production_id
        if production and (self.has_tracking == 'none' or production.use_auto_consume_components_lots) and ((self.product_id in production.workorder_ids.quality_point_ids.component_id) or self.operation_id):
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
