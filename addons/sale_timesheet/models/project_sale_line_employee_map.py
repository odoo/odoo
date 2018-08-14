# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _name = 'project.sale.line.employee.map'

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
        ('uniq_map_sale_line_employee_per_project', 'UNIQUE(project_id,employee_id)', 'You can only map one employee with sale order item per project.'),
    ]
