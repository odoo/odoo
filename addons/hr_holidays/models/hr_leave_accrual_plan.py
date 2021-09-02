# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccrualPlan(models.Model):
    _name = "hr.leave.accrual.plan"
    _description = "Accrual Plan"

    name = fields.Char('Name', required=True)
    time_off_type_id = fields.Many2one('hr.leave.type', string="Time Off Type")
    employees_count = fields.Integer("Employees", compute='_compute_employee_count')
    level_ids = fields.One2many('hr.leave.accrual.level', 'accrual_plan_id')
    allocation_ids = fields.One2many('hr.leave.allocation', 'accrual_plan_id')
    transition_mode = fields.Selection([
        ('immediately', 'Immediately'),
        ('end_of_accrual', "After this accrual's period")],
        string="Level Transition", default="immediately", required=True,
        help="""Immediately: When the date corresponds to the new level, your accrual is automatically computed, granted and you switch to new level
                After this accrual's period: When the accrual is complete (a week, a month), and granted, you switch to next level if allocation date corresponds""")

    @api.depends('allocation_ids')
    def _compute_employee_count(self):
        allocations_read_group = self.env['hr.leave.allocation'].read_group(
            [('accrual_plan_id', 'in', self.ids)],
            ['accrual_plan_id', 'employee_count:count_distinct(employee_id)'],
            ['accrual_plan_id'],
        )
        allocations_dict = {res['accrual_plan_id'][0]: res['employee_count'] for res in allocations_read_group}
        for plan in self:
            plan.employees_count = allocations_dict.get(plan.id, 0)

    def action_open_accrual_plan_employees(self):
        self.ensure_one()

        return {
            'name': _("Accrual Plan's Employees"),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', self.allocation_ids.employee_id.ids)],
        }
