# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _name = 'project.sale.line.employee.map'
    _description = 'Project Sales line, employee mapping'

    @api.model
    def _default_project_id(self):
        if self._context.get('active_id'):
            return self._context['active_id']
        return False

    project_id = fields.Many2one('project.project', "Project", domain=[('billable_type', '!=', 'no')], required=True, default=_default_project_id)
    employee_id = fields.Many2one('hr.employee', "Employee", required=True)
    sale_line_id = fields.Many2one('sale.order.line', "Sale Order Item", domain=[('is_service', '=', True)], required=True)
    price_unit = fields.Float(related='sale_line_id.price_unit', readonly=True)

    _sql_constraints = [
        ('uniqueness_employee', 'UNIQUE(project_id,employee_id)', 'An employee cannot be selected more than once in the mapping. Please remove duplicate(s) and try again.'),
    ]
