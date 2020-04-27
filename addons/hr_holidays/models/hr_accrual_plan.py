# # -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AccrualPlan(models.Model):
    _name = "hr.leave.accrual.plan"
    _description = "Accrual Plan"

    name = fields.Char('Accrual Plan', required=True)
    accrual_ids = fields.One2many('hr.leave.accrual', 'plan_id', string='Accruals')
    allocation_ids = fields.One2many('hr.leave.allocation', 'accrual_plan_id')
    allocation_item_ids = fields.One2many('hr.leave.allocation.item', 'accrual_plan_id', compute='_compute_allocation_item')
    employees_count = fields.Integer("Employees", compute='_compute_employee_count')
    allocation_count = fields.Integer("Allocations", compute='_compute_allocation_count')

    @api.depends('allocation_ids')
    def _compute_allocation_item(self):
        for plan in self:
            items = self.env['hr.leave.allocation.item'].search([('accrual_plan_id', '=', plan.id)])
            plan.allocation_item_ids = [(6, 0, items.ids)]


    @api.depends('allocation_ids', 'allocation_item_ids')
    def _compute_employee_count(self):
        for plan in self:
            plan.employees_count = len(plan.allocation_item_ids.mapped('employee_id').ids)



    @api.depends('allocation_ids')
    def _compute_allocation_count(self):
        for plan in self:
            plan.allocation_count = len(plan.allocation_ids.ids)

    def action_open_accrual_plan_employees(self):
        self.ensure_one()

        return {
            'name': _("Accrual Plan's Employees"),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', self.allocation_item_ids.mapped('employee_id').ids)],
        }

    def action_open_accrual_plan_allocations(self):
        self.ensure_one()
        # The sql constraint prevent to have more than one allocation per plan
        return {
            'name': _("Accrual Plan's Allocations"),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'res_model': 'hr.leave.allocation',
            "context": {"create": False},
            'domain': [('accrual_plan_id', '=', self.id)],
        }

    def create_allocation(self):
        ctx = dict(self._context)
        ctx.update({'default_allocation_type': 'accrual', 'default_accrual_plan_id': self.id})
        return {
            "private_name": _("Allocation for accrual plan %(plan_name)s", plan_name=self.name),
            "view_mode": "form",
            "res_model": "hr.leave.allocation",
            "type": "ir.actions.act_window",
            "context": ctx,
            "target": 'new,'
        }
