# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class QualityPoint(models.Model):
    _inherit = "quality.point"

    @api.model
    def _get_domain_for_production(self, quality_points_domain):
        return quality_points_domain

    @api.onchange('measure_on', 'picking_type_ids')
    def _onchange_measure_on(self):
        if self.measure_on == 'move_line' and any(pt.code == 'mrp_operation' for pt in self.picking_type_ids):
            message = _("It will not be possible to edit the failed quantity of a quantity type quality check on a manufacturing order")
            return {'warning': {'title': _('Warning'), 'message': message}}


class QualityCheck(models.Model):
    _inherit = "quality.check"

    production_id = fields.Many2one(
        'mrp.production', 'Production Order', check_company=True)

    def do_fail(self):
        self.ensure_one()
        res = super().do_fail()
        if self.production_id and self.production_id.product_id.tracking == 'serial' and self.move_line_id:
            self.move_line_id.move_id.picked = False
        return res

    @api.depends("production_id.qty_producing")
    def _compute_qty_line(self):
        record_without_production = self.env['quality.check']
        for qc in self:
            if qc.production_id:
                qc.qty_line = qc.production_id.qty_producing
            else:
                record_without_production |= qc
        return super(QualityCheck, record_without_production)._compute_qty_line()

    def _can_move_line_to_failure_location(self):
        self.ensure_one()
        if self.production_id and self.quality_state == 'fail' and self.point_id.measure_on == 'move_line':
            mo = self.production_id
            move = mo.move_finished_ids.filtered(lambda m: m.product_id == mo.product_id)
            move.quantity = mo.qty_producing
            self.move_line_id = move.move_line_ids[:1]
            self.lot_line_id = mo.lot_producing_id
            return True

        return super()._can_move_line_to_failure_location()

    def _move_line_to_failure_location(self, failure_location_id, failed_qty=None):
        res = super()._move_line_to_failure_location(failure_location_id, failed_qty=failed_qty)
        for check in self:
            if check.production_id and check.move_line_id:
                check.move_line_id.move_id.picked = False  # to not update qty_produced
        return res


class QualityAlert(models.Model):
    _inherit = "quality.alert"

    production_id = fields.Many2one(
        'mrp.production', "Production Order", check_company=True)
