# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _name = 'project.sale.line.employee.map'
    _description = 'Project Sales line, employee mapping'

    project_id = fields.Many2one('project.project', "Project", required=True)
    employee_id = fields.Many2one('hr.employee', "Employee", required=True)
    sale_line_id = fields.Many2one(
        'sale.order.line', "Sales Order Item",
        compute="_compute_sale_line_id", store=True, readonly=False,
        domain="""[
            ('is_service', '=', True),
            ('is_expense', '=', False),
            ('state', 'in', ['sale', 'done']),
            ('order_partner_id', '=?', partner_id),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)]""")
    company_id = fields.Many2one('res.company', string='Company', related='project_id.company_id')
    partner_id = fields.Many2one(related='project_id.partner_id')
    price_unit = fields.Float("Unit Price", compute='_compute_price_unit', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", compute='_compute_currency_id', store=True, readonly=False)
    cost = fields.Monetary(currency_field='cost_currency_id', compute='_compute_cost', store=True, readonly=False,
                           help="This cost overrides the employee's default employee hourly wage in employee's HR Settings")
    display_cost = fields.Monetary(currency_field='cost_currency_id', compute="_compute_display_cost", inverse="_inverse_display_cost", string="Hourly Cost")
    cost_currency_id = fields.Many2one('res.currency', string="Cost Currency", related='employee_id.currency_id', readonly=True)
    is_cost_changed = fields.Boolean('Is Cost Manually Changed', compute='_compute_is_cost_changed', store=True)

    _sql_constraints = [
        ('uniqueness_employee', 'UNIQUE(project_id,employee_id)', 'An employee cannot be selected more than once in the mapping. Please remove duplicate(s) and try again.'),
    ]

    @api.depends('partner_id')
    def _compute_sale_line_id(self):
        self.filtered(
            lambda map_entry:
                map_entry.sale_line_id
                and map_entry.partner_id
                and map_entry.sale_line_id.order_partner_id.commercial_partner_id != map_entry.partner_id.commercial_partner_id
        ).update({'sale_line_id': False})

    @api.depends('sale_line_id.price_unit')
    def _compute_price_unit(self):
        for line in self:
            if line.sale_line_id:
                line.price_unit = line.sale_line_id.price_unit
            else:
                line.price_unit = 0

    @api.depends('sale_line_id.price_unit')
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = line.sale_line_id.currency_id if line.sale_line_id else False

    @api.depends('employee_id.hourly_cost')
    def _compute_cost(self):
        self.env.remove_to_compute(self._fields['is_cost_changed'], self)
        for map_entry in self:
            if not map_entry.is_cost_changed:
                map_entry.cost = map_entry.employee_id.hourly_cost or 0.0

    def _get_working_hours_per_calendar(self, is_uom_day=False):
        resource_calendar_per_hours = {}

        if not is_uom_day:
            return resource_calendar_per_hours

        read_group_data = self.env['resource.calendar']._read_group(
            [('id', 'in', self.employee_id.resource_calendar_id.ids)],
            ['ids:array_agg(id)', 'hours_per_day'],
            ['hours_per_day'],
        )
        for res in read_group_data:
            for calendar_id in res.get('ids', []):
                resource_calendar_per_hours[calendar_id] = res.get('hours_per_day')

        return resource_calendar_per_hours

    @api.depends_context('company')
    @api.depends('cost', 'employee_id.resource_calendar_id')
    def _compute_display_cost(self):
        is_uom_day = self.env.ref('uom.product_uom_day') == self.env.company.timesheet_encode_uom_id
        resource_calendar_per_hours = self._get_working_hours_per_calendar(is_uom_day)

        for map_line in self:
            if is_uom_day:
                map_line.display_cost = map_line.cost * resource_calendar_per_hours.get(map_line.employee_id.resource_calendar_id.id, 1)
            else:
                map_line.display_cost = map_line.cost

    def _inverse_display_cost(self):
        is_uom_day = self.env.ref('uom.product_uom_day') == self.env.company.timesheet_encode_uom_id
        resource_calendar_per_hours = self._get_working_hours_per_calendar(is_uom_day)

        for map_line in self:
            if is_uom_day:
                map_line.cost = map_line.display_cost / resource_calendar_per_hours.get(map_line.employee_id.resource_calendar_id.id, 1)
            else:
                map_line.cost = map_line.display_cost

    @api.depends('cost')
    def _compute_is_cost_changed(self):
        for map_entry in self:
            map_entry.is_cost_changed = map_entry.employee_id and map_entry.cost != map_entry.employee_id.hourly_cost

    @api.model_create_multi
    def create(self, vals_list):
        maps = super().create(vals_list)
        maps._update_project_timesheet()
        return maps

    def write(self, values):
        res = super(ProjectProductEmployeeMap, self).write(values)
        self._update_project_timesheet()
        return res

    def _update_project_timesheet(self):
        self.filtered(lambda l: l.sale_line_id).project_id._update_timesheets_sale_line_id()
