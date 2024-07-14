# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv.expression import AND
from odoo.exceptions import UserError


class QualityPoint(models.Model):
    _inherit = "quality.point"

    @api.model
    def _get_domain_for_production(self, quality_points_domain):
        quality_points_domain = super()._get_domain_for_production(quality_points_domain)
        return AND([quality_points_domain, [('operation_id', '=', False)]])

    @api.constrains('measure_on', 'picking_type_ids')
    def _check_picking_type_ids(self):
        for point in self:
            if point.measure_on == 'move_line' and self.operation_id and any(picking_type.code == 'mrp_operation' for picking_type in point.picking_type_ids):
                raise UserError(_("The Quantity quality check type is not possible with manufacturing operation types."))


class QualityCheck(models.Model):
    _inherit = "quality.check"

    operation_id = fields.Many2one(related="point_id.operation_id")

    def do_pass(self):
        self.ensure_one()
        super().do_pass()

    def do_fail(self):
        self.ensure_one()
        return super().do_fail()

    def do_measure(self):
        self.ensure_one()
        res = super().do_measure()
        return self._next() if self.workorder_id else res


    def _next(self, continue_production=False):
        self.ensure_one()
        result = super()._next(continue_production=continue_production)
        if self.quality_state == 'fail' and (self.warning_message or self.failure_message):
            return {
                'name': _('Quality Check Failed'),
                'type': 'ir.actions.act_window',
                'res_model': 'quality.check.wizard',
                'views': [(self.env.ref('quality_control.quality_check_wizard_form_failure').id, 'form')],
                'target': 'new',
                'context': {
                    **self.env.context,
                    'default_check_ids': [self.id],
                    'default_current_check_id': self.id,
                    'default_test_type': self.test_type,
                    'default_failure_message': self.failure_message,
                    'default_warning_message': self.warning_message,
                },
            }
        return result

    def _get_check_result(self):
        if self.test_type == 'passfail':
            return _('Success') if self.quality_state == 'pass' else _('Failure')
        elif self.test_type == 'measure':
            return '{} {}'.format(self.measure, self.norm_unit)
        return super(QualityCheck, self)._get_check_result()

    def _check_to_unlink(self):
        self.ensure_one()
        return super()._check_to_unlink() and not self.workorder_id

    def _update_lot_from_lot_line(self):
        self.ensure_one()
        return super()._update_lot_from_lot_line() and (not self.production_id or self.move_id.picking_type_id.prefill_lot_tablet)

    def action_pass_and_next(self):
        self.ensure_one()
        super().do_pass()
        return self._next()

    def action_fail_and_next(self):
        self.ensure_one()
        super().do_fail()
        return self._next()
