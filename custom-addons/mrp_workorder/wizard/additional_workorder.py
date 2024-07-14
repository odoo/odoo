# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MrpWorkorderAdditionalWorkorder(models.TransientModel):
    _name = "mrp_production.additional.workorder"
    _description = "Additional Workorder"

    production_id = fields.Many2one(
        'mrp.production', required=True,
        default=lambda self: self.env.context.get('active_id', None),
    )
    name = fields.Char('Operation name', required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', required=True)
    duration_expected = fields.Float('Expected Duration')
    date_start = fields.Datetime('Start')
    company_id = fields.Many2one(related='production_id.company_id')
    employee_assigned_ids = fields.Many2many(
        'hr.employee', 'mrp_workorder_additional_employee_assigned',
        'additional_workorder_id', 'employee_id', string='Assigned'
    )

    def add_workorder(self):
        """Create production workorder for the additional workorder."""
        wo = self.env['mrp.workorder'].create({
            'production_id': self.production_id.id,
            'name': self.name,
            'workcenter_id': self.workcenter_id.id,
            'duration_expected': self.duration_expected,
            'date_start': self.date_start,
            'employee_assigned_ids': self.employee_assigned_ids.ids,
            'product_uom_id': self.production_id.product_uom_id.id,
            'blocked_by_workorder_ids': self.production_id.workorder_ids.ids,
        })
        if wo.date_start:
            wo.date_finished = wo._calculate_date_finished()
