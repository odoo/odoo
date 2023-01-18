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
        help="""Specify what occurs if a level transition takes place in the middle of a pay period.\n
                'Immediately' will switch the employee to the new accrual level on the exact date during the ongoing pay period.\n
                'After this accrual's period' will keep the employee on the same accrual level until the ongoing pay period is complete.
                After it is complete, the new level will take effect when the next pay period begins.""")
    show_transition_mode = fields.Boolean(compute='_compute_show_transition_mode')

    @api.depends('level_ids')
    def _compute_show_transition_mode(self):
        for plan in self:
            plan.show_transition_mode = len(plan.level_ids) > 1

    level_count = fields.Integer('Levels', compute='_compute_level_count')

    @api.depends('level_ids')
    def _compute_level_count(self):
        level_aggregate = self.env['hr.leave.accrual.level']._aggregate(
            [('accrual_plan_id', 'in', self.ids)],
            aggregates=['*:count'],
            groupby=['accrual_plan_id'],
        )
        for plan in self:
            plan.level_count = level_aggregate.get_agg(plan, '*:count', 0)

    @api.depends('allocation_ids')
    def _compute_employee_count(self):
        allocations_aggregate = self.env['hr.leave.allocation']._aggregate(
            [('accrual_plan_id', 'in', self.ids)],
            ['employee_id:count_distinct'],
            ['accrual_plan_id'],
        )
        for plan in self:
            plan.employees_count = allocations_aggregate.get_agg(plan, 'employee_id:count_distinct', 0)

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
