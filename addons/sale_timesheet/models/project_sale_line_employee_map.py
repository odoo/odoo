# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _name = 'project.sale.line.employee.map'
    _description = 'Project Sales line, employee mapping'

    project_id = fields.Many2one('project.project', "Project", required=True)
    employee_id = fields.Many2one('hr.employee', "Employee", required=True)
    sale_line_id = fields.Many2one('sale.order.line', "Sale Order Item", compute="_compute_sale_line_id", store=True, readonly=False, required=True,
        domain="""[
            ('is_service', '=', True),
            ('is_expense', '=', False),
            ('state', 'in', ['sale', 'done']),
            ('order_partner_id', '=', partner_id),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)]""")
    company_id = fields.Many2one('res.company', string='Company', related='project_id.company_id')
    partner_id = fields.Many2one(related='project_id.partner_id')
    price_unit = fields.Float("Unit Price", compute='_compute_price_unit', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", compute='_compute_price_unit', store=True, readonly=False)

    _sql_constraints = [
        ('uniqueness_employee', 'UNIQUE(project_id,employee_id)', 'An employee cannot be selected more than once in the mapping. Please remove duplicate(s) and try again.'),
    ]

    @api.depends('project_id.partner_id')
    def _compute_sale_line_id(self):
        self.filtered(lambda map_entry: map_entry.sale_line_id.order_partner_id != map_entry.project_id.partner_id).update({'sale_line_id': False})

    @api.depends('sale_line_id', 'sale_line_id.price_unit')
    def _compute_price_unit(self):
        for line in self:
            if line.sale_line_id:
                line.price_unit = line.sale_line_id.price_unit
                line.currency_id = line.sale_line_id.currency_id
            else:
                line.price_unit = 0
                line.currency_id = False

    @api.model
    def create(self, values):
        res = super(ProjectProductEmployeeMap, self).create(values)
        res._update_project_timesheet()
        return res

    def write(self, values):
        res = super(ProjectProductEmployeeMap, self).write(values)
        self._update_project_timesheet()
        return res

    def _update_project_timesheet(self):
        self.filtered(lambda l: l.sale_line_id).project_id._update_timesheets_sale_line_id()
