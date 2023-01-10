# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccrualPlan(models.Model):
    _name = "hr.leave.accrual.plan"
    _description = "Accrual Plan"

    name = fields.Char('Name', required=True)
    time_off_type_id = fields.Many2one('hr.leave.type', string="Time Off Type",
        help="""Specify if this accrual plan can only be used with this Time Off Type.
                Leave empty if this accrual plan can be used with any Time Off Type.""")
    employees_count = fields.Integer("Employees", compute='_compute_employee_count')
    level_ids = fields.One2many('hr.leave.accrual.level', 'accrual_plan_id', copy=True)
    allocation_ids = fields.One2many('hr.leave.allocation', 'accrual_plan_id')
    transition_mode = fields.Selection([
        ('immediately', 'Immediately'),
        ('end_of_accrual', "After this accrual's period")],
        string="Level Transition", default="immediately", required=True,
        help="""Immediately: When the date corresponds to the new level, your accrual is automatically computed, granted and you switch to new level
                After this accrual's period: When the accrual is complete (a week, a month), and granted, you switch to next level if allocation date corresponds""")
    level_count = fields.Integer('Levels', compute='_compute_level_count')

    @api.depends('level_ids')
    def _compute_level_count(self):
        level_read_group = self.env['hr.leave.accrual.level'].read_group(
            [('accrual_plan_id', 'in', self.ids)],
            fields=['accrual_plan_id'],
            groupby=['accrual_plan_id'],
        )
        mapped_count = {group['accrual_plan_id'][0]: group['accrual_plan_id_count'] for group in level_read_group}
        for plan in self:
            plan.level_count = mapped_count.get(plan.id, 0)

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

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {},
                       name=_("%s (copy)", self.name))
        return super().copy(default=default)
