# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# YTI PLEASE SPLIT ME
class Project(models.Model):
    _inherit = 'project.project'

    @api.model
    def default_get(self, fields):
        """ Pre-fill timesheet product as "Time" data product when creating new project allowing billable tasks by default. """
        result = super(Project, self).default_get(fields)
        if 'timesheet_product_id' in fields and result.get('allow_billable') and result.get('allow_timesheets') and not result.get('timesheet_product_id'):
            default_product = self.env.ref('sale_timesheet.time_product', False)
            if default_product:
                result['timesheet_product_id'] = default_product.id
        return result

    def _default_timesheet_product_id(self):
        return self.env.ref('sale_timesheet.time_product', False)

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
    display_create_order = fields.Boolean(compute='_compute_display_create_order')
    timesheet_product_id = fields.Many2one(
        'product.product', string='Timesheet Product', 
        domain="""[
            ('type', '=', 'service'),
            ('invoice_policy', '=', 'delivery'),
            ('service_type', '=', 'timesheet'),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)]""",
        help='Select a Service product with which you would like to bill your time spent on tasks.',
        default=_default_timesheet_product_id)

    _sql_constraints = [
        ('timesheet_product_required_if_billable_and_timesheets', "CHECK((allow_billable = 't' AND allow_timesheets = 't' AND timesheet_product_id IS NOT NULL) OR (allow_billable = 'f') OR (allow_timesheets = 'f'))", 'The timesheet product is required when the task can be billed and timesheets are allowed.'),
    ]

    @api.depends('billable_type', 'allow_billable', 'sale_order_id', 'partner_id')
    def _compute_display_create_order(self):
        for project in self:
            project._compute_billable_type()
            show = True
            if not project.partner_id or project.billable_type != 'no' or project.allow_billable or project.sale_order_id:
                show = False
            project.display_create_order = show

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

    @api.depends('allow_timesheets', 'allow_billable')
    def _compute_timesheet_product_id(self):
        default_product = self.env.ref('sale_timesheet.time_product', False)
        for project in self:
            if not project.allow_timesheets or not project.allow_billable:
                project.timesheet_product_id = False
            elif not project.timesheet_product_id:
                project.timesheet_product_id = default_product

    @api.depends('allow_billable')
    def _compute_allow_billable(self):
        """ In order to keep task billable type as 'task_rate' using sale_timesheet usual flow.
            (see _compute_billable_type method in sale_timesheet)
        """
        self.filtered(lambda p: p.allow_billable).update({
            'sale_order_id': False,
            'sale_line_employee_ids': False,
        })

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
                'default_product_id': self.timesheet_product_id.id,
            },
        }


class ProjectTask(models.Model):
    _inherit = "project.task"

    # override sale_order_id and make it computed stored field instead of regular field.
    sale_order_id = fields.Many2one(compute='_compute_sale_order_id', store=True, readonly=False,
    domain="['|', '|', ('partner_id', '=', partner_id), ('partner_id', 'child_of', commercial_partner_id), ('partner_id', 'parent_of', partner_id)]")
    analytic_account_id = fields.Many2one('account.analytic.account', related='sale_order_id.analytic_account_id')
    billable_type = fields.Selection([
        ('task_rate', 'At Task Rate'),
        ('employee_rate', 'At Employee Rate'),
        ('no', 'No Billable')
    ], string="Billable Type", compute='_compute_billable_type', compute_sudo=True, store=True)
    is_project_map_empty = fields.Boolean("Is Project map empty", compute='_compute_is_project_map_empty')
    has_multi_sol = fields.Boolean(compute='_compute_has_multi_sol', compute_sudo=True)
    allow_billable = fields.Boolean(related="project_id.allow_billable")
    display_create_order = fields.Boolean(compute='_compute_display_create_order')

    @api.depends(
        'allow_billable', 'allow_timesheets', 'sale_order_id', 'display_timesheet_timer',
        'timer_start')
    def _compute_display_create_order(self):
        for task in self:
            show = True
            if not task.allow_billable or not task.allow_timesheets or \
                task.billable_type == 'employee_rate' or not task.partner_id or \
                task.sale_order_id or (task.display_timesheet_timer and task.timer_start):
                show = False
            task.display_create_order = show

    @api.onchange('sale_line_id')
    def _onchange_sale_line_id(self):
        if self._get_timesheet() and self.allow_timesheets:
            if self.sale_line_id:
                if self.sale_line_id.product_id.service_policy == 'delivered_timesheet' and self._origin.sale_line_id.product_id.service_policy == 'delivered_timesheet':
                    message = _("All timesheet hours that are not yet invoiced will be assigned to the selected Sales Order Item on save. Discard to avoid the change.")
                else:
                    message = _("All timesheet hours will be assigned to the selected Sales Order Item on save. Discard to avoid the change.")
            else:
                message = _("All timesheet hours that are not yet invoiced will be removed from the selected Sales Order Item on save. Discard to avoid the change.")

            return {'warning': {
                'title': _("Warning"),
                'message': message
            }}

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self._origin.allow_timesheets and self._get_timesheet():
            message = _("All timesheet hours that are not yet invoiced will be assigned to the selected Project on save. Discard to avoid the change.")

            return {'warning': {
                'title': _("Warning"),
                'message': message
            }}

    @api.depends('analytic_account_id.active')
    def _compute_analytic_account_active(self):
        super()._compute_analytic_account_active()
        for task in self:
            task.analytic_account_active = task.analytic_account_active or task.analytic_account_id.active

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

    @api.depends('timesheet_ids')
    def _compute_has_multi_sol(self):
        for task in self:
            task.has_multi_sol = task.timesheet_ids.so_line != task.sale_line_id

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
        old_sale_line_id = dict([(t.id, t.sale_line_id.id) for t in self])
        if values.get('project_id'):
            project_dest = self.env['project.project'].browse(values['project_id'])
            if project_dest.billable_type == 'employee_rate':
                values['sale_line_id'] = False
        res = super(ProjectTask, self).write(values)
        if 'sale_line_id' in values and self.filtered('allow_timesheets').sudo().timesheet_ids:
            so = self.env['sale.order.line'].browse(values['sale_line_id']).order_id
            if so and not so.analytic_account_id:
                so.analytic_account_id = self.project_id.analytic_account_id
            timesheet_ids = self.filtered('allow_timesheets').timesheet_ids.filtered(
                lambda t: (not t.timesheet_invoice_id or t.timesheet_invoice_id.state == 'cancel') and t.so_line.id == old_sale_line_id[t.task_id.id]
            )
            timesheet_ids.write({'so_line': values['sale_line_id']})
            if 'project_id' in values:

                # Special case when we edit SOL an project in same time, as we edit SOL of
                # timesheet lines, function '_get_timesheet' won't find the right timesheet
                # to edit so we must edit those here.
                project = self.env['project.project'].browse(values.get('project_id'))
                if project.allow_timesheets:
                    timesheet_ids.write({'project_id': values.get('project_id')})
        return res

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
                'default_product_id': self.project_id.timesheet_product_id.id,
            },
        }

    def _get_timesheet(self):
        # return not invoiced timesheet and timesheet without so_line or so_line linked to task
        timesheet_ids = super(ProjectTask, self)._get_timesheet()
        return timesheet_ids.filtered(lambda t: (not t.timesheet_invoice_id or t.timesheet_invoice_id.state == 'cancel') and (not t.so_line or t.so_line == t.task_id._origin.sale_line_id))

    def _get_action_view_so_ids(self):
        return list(set((self.sale_order_id + self.timesheet_ids.so_line.order_id).ids))
