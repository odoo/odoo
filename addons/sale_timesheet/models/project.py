# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = 'project.project'

    billable_type = fields.Selection([
        ('task_rate', 'At Task Rate'),
        ('employee_rate', 'At Employee Rate'),
        ('no', 'No Billable')
    ], string="Billable Type", compute='_compute_billable_type', compute_sudo=True, store=True,
        help='At which rate timesheets will be billed:\n'
        ' - At task rate: each time spend on a task is billed at task rate.\n'
        ' - At employee rate: each employee log time billed at his rate.\n'
        ' - No Billable: track time without invoicing it')
    sale_line_employee_ids = fields.One2many('project.sale.line.employee.map', 'project_id', "Sale line/Employee map", copy=False,
        help="Employee/Sale Order Item Mapping:\n Defines to which sales order item an employee's timesheet entry will be linked."
        "By extension, it defines the rate at which an employee's time on the project is billed.")
    allow_billable = fields.Boolean("Bill from Tasks")

    @api.depends('sale_order_id', 'sale_line_id', 'sale_line_employee_ids')
    def _compute_billable_type(self):
        for project in self:
            billable_type = 'no'
            if project.sale_order_id:
                if project.sale_line_employee_ids:
                    billable_type = 'employee_rate'
                else:
                    billable_type = 'task_rate'
            project.billable_type = billable_type

    @api.onchange('sale_line_employee_ids', 'billable_type')
    def _onchange_sale_line_employee_ids(self):
        if self.billable_type == 'task_rate':
            if self.sale_line_employee_ids:
                self.billable_type = 'employee_rate'
        else:
            if self.billable_type == 'no':
                self.sale_line_employee_ids = False

    @api.onchange('allow_billable')
    def _onchange_allow_billable(self):
        """ In order to keep task billable type as 'task_rate' using sale_timesheet usual flow.
            (see _compute_billable_type method in sale_timesheet)
        """
        if self.allow_billable:
            self.sale_order_id = False
            self.sale_line_employee_ids = False

    @api.constrains('sale_line_id', 'billable_type')
    def _check_sale_line_type(self):
        for project in self:
            if project.billable_type == 'task_rate':
                if project.sale_line_id and not project.sale_line_id.is_service:
                    raise ValidationError(_("A billable project should be linked to a Sales Order Item having a Service product."))
                if project.sale_line_id and project.sale_line_id.is_expense:
                    raise ValidationError(_("A billable project should be linked to a Sales Order Item that does not come from an expense or a vendor bill."))

    def action_view_timesheet(self):
        self.ensure_one()
        if self.allow_timesheets:
            return self.action_view_timesheet_plan()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheets of %s') % self.name,
            'domain': [('project_id', '!=', False)],
            'res_model': 'account.analytic.line',
            'view_id': False,
            'view_mode': 'tree,form',
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    Record timesheets
                </p><p>
                    You can register and track your workings hours by project every
                    day. Every time spent on a project will become a cost and can be re-invoiced to
                    customers if required.
                </p>
            """),
            'limit': 80,
            'context': {
                'default_project_id': self.id,
                'search_default_project_id': [self.id]
            }
        }

    def action_view_timesheet_plan(self):
        action = self.env.ref('sale_timesheet.project_timesheet_action_client_timesheet_plan').read()[0]
        action['params'] = {
            'project_ids': self.ids,
        }
        action['context'] = {
            'active_id': self.id,
            'active_ids': self.ids,
            'search_default_name': self.name,
        }
        return action

    def action_make_billable(self):
        return {
            "name": _("Create Sales Order"),
            "type": 'ir.actions.act_window',
            "res_model": 'project.create.sale.order',
            "views": [[False, "form"]],
            "target": 'new',
            "context": {
                'active_id': self.id,
                'active_model': 'project.project',
            },
        }


class ProjectTask(models.Model):
    _inherit = "project.task"

    # override sale_order_id and make it computed stored field instead of regular field.
    sale_order_id = fields.Many2one(compute='_compute_sale_order_id', store=True, readonly=False)
    billable_type = fields.Selection([
        ('task_rate', 'At Task Rate'),
        ('employee_rate', 'At Employee Rate'),
        ('no', 'No Billable')
    ], string="Billable Type", compute='_compute_billable_type', compute_sudo=True, store=True)
    is_project_map_empty = fields.Boolean("Is Project map empty", compute='_compute_is_project_map_empty')
    allow_billable = fields.Boolean(related="project_id.allow_billable")

    @api.depends('sale_line_id', 'project_id', 'billable_type')
    def _compute_sale_order_id(self):
        for task in self:
            if task.billable_type == 'task_rate':
                task.sale_order_id = task.sale_line_id.order_id or task.project_id.sale_order_id
            elif task.billable_type == 'employee_rate':
                task.sale_order_id = task.project_id.sale_order_id
            elif task.billable_type == 'no':
                task.sale_order_id = False

    @api.depends('project_id.billable_type', 'sale_line_id')
    def _compute_billable_type(self):
        for task in self:
            billable_type = 'no'
            if task.project_id.billable_type == 'employee_rate':
                billable_type = task.project_id.billable_type
            elif (task.project_id.billable_type in ['task_rate', 'no'] and task.sale_line_id):  # create a task in global project (non billable)
                billable_type = 'task_rate'
            task.billable_type = billable_type

    @api.depends('project_id.sale_line_employee_ids')
    def _compute_is_project_map_empty(self):
        for task in self:
            task.is_project_map_empty = not bool(task.sudo().project_id.sale_line_employee_ids)

    @api.onchange('project_id')
    def _onchange_project(self):
        super(ProjectTask, self)._onchange_project()
        if self.project_id:
            if self.project_id.billable_type == 'employee_rate':
                if not self.partner_id:
                    self.partner_id = self.project_id.sale_order_id.partner_id
            elif self.project_id.billable_type == 'task_rate':
                if not self.sale_line_id:
                    self.sale_line_id = self.project_id.sale_line_id
                if not self.partner_id:
                    self.partner_id = self.sale_line_id.order_partner_id
        # set domain on SO: on non billable project, all SOL of customer, otherwise the one from the SO

    def write(self, values):
        if values.get('project_id'):
            project_dest = self.env['project.project'].browse(values['project_id'])
            if project_dest.billable_type == 'employee_rate':
                values['sale_line_id'] = False
        return super(ProjectTask, self).write(values)

    def action_make_billable(self):
        return {
            "name": _("Create Sales Order"),
            "type": 'ir.actions.act_window',
            "res_model": 'project.task.create.sale.order',
            "views": [[False, "form"]],
            "target": 'new',
            "context": {
                'active_id': self.id,
                'active_model': 'project.task',
                'form_view_initial_mode': 'edit',
            },
        }
