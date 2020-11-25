# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _name = 'project.sale.line.employee.map'
    _description = 'Project Sales line, employee mapping'

    project_id = fields.Many2one('project.project', "Project", required=True)
    employee_id = fields.Many2one('hr.employee', "Employee", required=True)
    sale_line_id = fields.Many2one('sale.order.line', "Sale Order Item", domain=[('is_service', '=', True)])
    company_id = fields.Many2one('res.company', string='Company', related='project_id.company_id')
    timesheet_product_id = fields.Many2one(
        'product.product', string='Service',
        domain="""[
            ('type', '=', 'service'),
            ('invoice_policy', '=', 'delivery'),
            ('service_type', '=', 'timesheet'),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)]""")
    price_unit = fields.Float("Unit Price", compute='_compute_price_unit', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", compute='_compute_price_unit', store=True, readonly=False)

    _sql_constraints = [
        ('uniqueness_employee', 'UNIQUE(project_id,employee_id)', 'An employee cannot be selected more than once in the mapping. Please remove duplicate(s) and try again.'),
    ]

    @api.depends('sale_line_id', 'sale_line_id.price_unit', 'timesheet_product_id')
    def _compute_price_unit(self):
        for line in self:
            if line.sale_line_id:
                line.price_unit = line.sale_line_id.price_unit
                line.currency_id = line.sale_line_id.currency_id
            elif line.timesheet_product_id:
                line.price_unit = line.timesheet_product_id.lst_price
                line.currency_id = line.timesheet_product_id.currency_id
            else:
                line.price_unit = 0
                line.currency_id = False

    @api.onchange('timesheet_product_id')
    def _onchange_timesheet_product_id(self):
        if self.timesheet_product_id:
            self.price_unit = self.timesheet_product_id.lst_price
        else:
            self.price_unit = 0.0

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
