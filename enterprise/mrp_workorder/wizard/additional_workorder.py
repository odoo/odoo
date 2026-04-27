# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, Command


class MrpWorkorderAdditionalWorkorder(models.TransientModel):
    _name = "mrp_production.additional.workorder"
    _description = "Additional Workorder"

    production_id = fields.Many2one(
        'mrp.production', required=True,
        default=lambda self: self.env.context.get('active_id', None),
    )
    name = fields.Char('Title', required=True)
    blocked_by_workorder_id = fields.Many2one('mrp.workorder',
                                     string="Insert after operation",
                                     domain="[('production_id', '=', production_id)]",
                                     copy=False)
    workcenter_id = fields.Many2one('mrp.workcenter', string="Work Center", required=True)
    duration_expected = fields.Float('Expected Duration')
    date_start = fields.Datetime('Date Start')
    company_id = fields.Many2one(related='production_id.company_id')
    employee_assigned_ids = fields.Many2many(
        'hr.employee', 'mrp_workorder_additional_employee_assigned',
        'additional_workorder_id', 'employee_id', string='Employee'
    )

    def add_workorder(self):
        """Create production workorder for the additional workorder."""
        if self.blocked_by_workorder_id:
            new_wo_sequence = self.blocked_by_workorder_id.sequence
        elif self.production_id.workorder_ids:
            new_wo_sequence = self.production_id.workorder_ids[0].sequence - 1
        else:
            new_wo_sequence = 100
        wo = self.env['mrp.workorder'].create({
            'production_id': self.production_id.id,
            'name': self.name,
            'sequence': new_wo_sequence,
            'workcenter_id': self.workcenter_id.id,
            'duration_expected': self.duration_expected,
            'date_start': self.date_start or self.blocked_by_workorder_id.date_finished,
            'employee_assigned_ids': self.employee_assigned_ids.ids,
            'product_uom_id': self.production_id.product_uom_id.id,
            'blocked_by_workorder_ids': [self.blocked_by_workorder_id.id] if self.blocked_by_workorder_id else False,
        })
        if wo.date_start:
            wo.date_finished = wo._calculate_date_finished()
        if self.blocked_by_workorder_id:
            # Make sure the new workorder will block the same workorders as the workorder it is blocked by.
            for next_wo in self.blocked_by_workorder_id.needed_by_workorder_ids:
                if next_wo.id != wo.id:
                    next_wo.blocked_by_workorder_ids = [Command.link(wo.id)]
        elif self.production_id.workorder_ids - wo:
            # If new WO is placed at the beginning, make sure it blocks the now second workorder
            self.production_id.workorder_ids.sorted()[1].blocked_by_workorder_ids = [Command.link(wo.id)]
