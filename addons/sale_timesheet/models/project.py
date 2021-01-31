# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

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

    bill_type = fields.Selection([
        ('customer_task', 'Different customers'),
        ('customer_project', 'A unique customer')
    ], string="Invoice Tasks to", default="customer_task",
        help='When billing tasks individually, a Sales Order will be created from each task. It is perfect if you would like to bill different services to different customers at different rates. \n When billing the whole project, a Sales Order will be created from the project instead. This option is better if you would like to bill all the tasks of a given project to a specific customer either at a fixed rate, or at an employee rate.')
    pricing_type = fields.Selection([
        ('fixed_rate', 'Project rate'),
        ('employee_rate', 'Employee rate')
    ], string="Pricing", default="fixed_rate",
        help='The fixed rate is perfect if you bill a service at a fixed rate per hour or day worked regardless of the employee who performed it. The employee rate is preferable if your employees deliver the same service at a different rate. For instance, junior and senior consultants would deliver the same service (= consultancy), but at a different rate because of their level of seniority.')
    sale_line_employee_ids = fields.One2many('project.sale.line.employee.map', 'project_id', "Sale line/Employee map", copy=False,
        help="Employee/Sale Order Item Mapping:\n Defines to which sales order item an employee's timesheet entry will be linked."
        "By extension, it defines the rate at which an employee's time on the project is billed.")
    allow_billable = fields.Boolean("Billable", help="Invoice your time and material from tasks.")
    display_create_order = fields.Boolean(compute='_compute_display_create_order')
    timesheet_product_id = fields.Many2one(
        'product.product', string='Timesheet Product',
        domain="""[
            ('type', '=', 'service'),
            ('invoice_policy', '=', 'delivery'),
            ('service_type', '=', 'timesheet'),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)]""",
        help='Select a Service product with which you would like to bill your time spent on tasks.',
        compute="_compute_timesheet_product_id", store=True, readonly=False,
        default=_default_timesheet_product_id)
    warning_employee_rate = fields.Boolean(compute='_compute_warning_employee_rate')

    _sql_constraints = [
        ('timesheet_product_required_if_billable_and_timesheets', """
            CHECK(
                (allow_billable = 't' AND allow_timesheets = 't' AND timesheet_product_id IS NOT NULL)
                OR (allow_billable IS NOT TRUE)
                OR (allow_timesheets IS NOT TRUE)
                OR (allow_billable IS NULL)
                OR (allow_timesheets IS NULL)
            )""", 'The timesheet product is required when the task can be billed and timesheets are allowed.'),

    ]

    @api.depends('allow_billable', 'sale_order_id', 'partner_id', 'bill_type')
    def _compute_display_create_order(self):
        for project in self:
            show = True
            if not project.partner_id or project.bill_type != 'customer_project' or not project.allow_billable or project.sale_order_id:
                show = False
            project.display_create_order = show

    @api.depends('allow_timesheets', 'allow_billable')
    def _compute_timesheet_product_id(self):
        default_product = self.env.ref('sale_timesheet.time_product', False)
        for project in self:
            if not project.allow_timesheets or not project.allow_billable:
                project.timesheet_product_id = False
            elif not project.timesheet_product_id:
                project.timesheet_product_id = default_product

    @api.depends('pricing_type', 'allow_timesheets', 'allow_billable', 'sale_line_employee_ids', 'sale_line_employee_ids.employee_id', 'bill_type')
    def _compute_warning_employee_rate(self):
        projects = self.filtered(lambda p: p.allow_billable and p.allow_timesheets and p.bill_type == 'customer_project' and p.pricing_type == 'employee_rate')
        tasks = projects.task_ids.filtered(lambda t: not t.non_allow_billable)
        employees = self.env['account.analytic.line'].read_group([('task_id', 'in', tasks.ids), ('non_allow_billable', '=', False)], ['employee_id', 'project_id'], ['employee_id', 'project_id'], ['employee_id', 'project_id'], lazy=False)
        dict_project_employee = defaultdict(list)
        for line in employees:
            dict_project_employee[line['project_id'][0]] += [line['employee_id'][0]]
        for project in projects:
            project.warning_employee_rate = any(x not in project.sale_line_employee_ids.employee_id.ids for x in dict_project_employee[project.id])

        (self - projects).warning_employee_rate = False

    @api.constrains('sale_line_id', 'pricing_type')
    def _check_sale_line_type(self):
        for project in self:
            if project.pricing_type == 'fixed_rate':
                if project.sale_line_id and not project.sale_line_id.is_service:
                    raise ValidationError(_("A billable project should be linked to a Sales Order Item having a Service product."))
                if project.sale_line_id and project.sale_line_id.is_expense:
                    raise ValidationError(_("A billable project should be linked to a Sales Order Item that does not come from an expense or a vendor bill."))

    @api.onchange('allow_billable')
    def _onchange_allow_billable(self):
        if self.task_ids._get_timesheet() and self.allow_timesheets and not self.allow_billable:
            message = _("All timesheet hours that are not yet invoiced will be removed from Sales Order on save. Discard to avoid the change.")
            return {'warning': {
                'title': _("Warning"),
                'message': message
            }}

    def write(self, values):
        res = super(Project, self).write(values)
        if 'allow_billable' in values and not values.get('allow_billable'):
            self.task_ids._get_timesheet().write({
                'so_line': False,
            })
        return res

    def _get_not_billed_timesheets(self):
        return self.sudo(False).mapped('timesheet_ids').filtered(
            lambda t: not t.timesheet_invoice_id or t.timesheet_invoice_id.state == 'cancel')

    def _update_timesheets_sale_line_id(self):
        for project in self.filtered(lambda p: p.allow_billable and p.allow_timesheets):
            timesheet_ids = project._get_not_billed_timesheets()
            if not timesheet_ids:
                continue
            for employee_id in project.sale_line_employee_ids.filtered(lambda l: l.project_id == project).employee_id:
                sale_line_id = project.sale_line_employee_ids.filtered(lambda l: l.project_id == project and l.employee_id == employee_id).sale_line_id
                timesheet_ids.filtered(lambda t: t.employee_id == employee_id).sudo().so_line = sale_line_id

    def action_view_timesheet(self):
        self.ensure_one()
        if self.allow_timesheets:
            return self.action_view_timesheet_plan()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheets of %s', self.name),
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
        action = self.env["ir.actions.actions"]._for_xml_id("sale_timesheet.project_timesheet_action_client_timesheet_plan")
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

    def action_view_so(self):
        self.ensure_one()
        action_window = {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "name": "Sales Order",
            "views": [[False, "form"]],
            "context": {"create": False, "show_sale": True},
            "res_id": self.sale_order_id.id
        }
        return action_window


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model
    def default_get(self, fields):
        result = super(ProjectTask, self).default_get(fields)

        if not result.get('timesheet_product_id', False) and 'project_id' in result:
            project = self.env['project.project'].browse(result['project_id'])
            if project.bill_type != 'customer_project' or project.pricing_type != 'employee_rate':
                result['timesheet_product_id'] = project.timesheet_product_id.id
        return result

    # override sale_order_id and make it computed stored field instead of regular field.
    sale_order_id = fields.Many2one(compute='_compute_sale_order_id', store=True, readonly=False,
    domain="['|', '|', ('partner_id', '=', partner_id), ('partner_id', 'child_of', commercial_partner_id), ('partner_id', 'parent_of', partner_id)]")
    analytic_account_id = fields.Many2one('account.analytic.account', related='sale_order_id.analytic_account_id')
    bill_type = fields.Selection(related="project_id.bill_type")
    pricing_type = fields.Selection(related="project_id.pricing_type")
    is_project_map_empty = fields.Boolean("Is Project map empty", compute='_compute_is_project_map_empty')
    has_multi_sol = fields.Boolean(compute='_compute_has_multi_sol', compute_sudo=True)
    allow_billable = fields.Boolean(related="project_id.allow_billable")
    display_create_order = fields.Boolean(compute='_compute_display_create_order')
    timesheet_product_id = fields.Many2one(
        'product.product', string='Service',
        domain="""[
            ('type', '=', 'service'),
            ('invoice_policy', '=', 'delivery'),
            ('service_type', '=', 'timesheet'),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)]""",
        help='Select a Service product with which you would like to bill your time spent on this task.')

    # TODO: [XBO] remove me in master
    non_allow_billable = fields.Boolean("Non-Billable", help="Your timesheets linked to this task will not be billed.")
    remaining_hours_so = fields.Float('Remaining Hours on SO', compute='_compute_remaining_hours_so')
    remaining_hours_available = fields.Boolean(related="sale_line_id.remaining_hours_available")

    @api.depends('sale_line_id', 'timesheet_ids', 'timesheet_ids.unit_amount')
    def _compute_remaining_hours_so(self):
        # TODO This is not yet perfectly working as timesheet.so_line stick to its old value although changed
        #      in the task From View.
        timesheets = self.timesheet_ids.filtered(lambda t: t.task_id.sale_line_id in (t.so_line, t._origin.so_line) and t.so_line.remaining_hours_available)

        mapped_remaining_hours = {task._origin.id: task.sale_line_id and task.sale_line_id.remaining_hours or 0.0 for task in self}
        uom_hour = self.env.ref('uom.product_uom_hour')
        for timesheet in timesheets:
            delta = 0
            if timesheet._origin.so_line == timesheet.task_id.sale_line_id:
                delta += timesheet._origin.unit_amount
            if timesheet.so_line == timesheet.task_id.sale_line_id:
                delta -= timesheet.unit_amount
            if delta:
                mapped_remaining_hours[timesheet.task_id._origin.id] += timesheet.so_line.product_uom._compute_quantity(delta, uom_hour)

        for task in self:
            task.remaining_hours_so = mapped_remaining_hours[task._origin.id]

    @api.depends(
        'allow_billable', 'allow_timesheets', 'sale_order_id')
    def _compute_display_create_order(self):
        for task in self:
            show = True
            if not task.allow_billable or not task.allow_timesheets or \
                (task.bill_type != 'customer_task' and not task.timesheet_product_id) or (not task.partner_id and task.bill_type != 'customer_task') or \
                task.sale_order_id or (task.bill_type != 'customer_task' and task.pricing_type != 'employee_rate'):
                show = False
            task.display_create_order = show

    @api.onchange('sale_line_id')
    def _onchange_sale_line_id(self):
        # TODO: remove me in master
        return

    @api.onchange('project_id')
    def _onchange_project_id(self):
        # TODO: remove me in master
        return

    @api.depends('analytic_account_id.active')
    def _compute_analytic_account_active(self):
        super()._compute_analytic_account_active()
        for task in self:
            task.analytic_account_active = task.analytic_account_active or task.analytic_account_id.active

    @api.depends('sale_line_id', 'project_id', 'allow_billable', 'non_allow_billable')
    def _compute_sale_order_id(self):
        for task in self:
            if not task.allow_billable or task.non_allow_billable:
                task.sale_order_id = False
            elif task.allow_billable:
                if task.sale_line_id:
                    task.sale_order_id = task.sale_line_id.sudo().order_id
                elif task.project_id.sale_order_id:
                    task.sale_order_id = task.project_id.sale_order_id
                if task.sale_order_id and not task.partner_id:
                    task.partner_id = task.sale_order_id.partner_id

    @api.depends('commercial_partner_id', 'sale_line_id.order_partner_id.commercial_partner_id', 'parent_id.sale_line_id', 'project_id.sale_line_id', 'allow_billable')
    def _compute_sale_line(self):
        billable_tasks = self.filtered('allow_billable')
        super(ProjectTask, billable_tasks)._compute_sale_line()
        for task in billable_tasks.filtered(lambda t: not t.sale_line_id):
            task.sale_line_id = task._get_last_sol_of_customer()

    @api.depends('project_id.sale_line_employee_ids')
    def _compute_is_project_map_empty(self):
        for task in self:
            task.is_project_map_empty = not bool(task.sudo().project_id.sale_line_employee_ids)

    @api.depends('timesheet_ids')
    def _compute_has_multi_sol(self):
        for task in self:
            task.has_multi_sol = task.timesheet_ids and task.timesheet_ids.so_line != task.sale_line_id

    @api.onchange('project_id')
    def _onchange_project(self):
        if self.project_id and self.project_id.bill_type == 'customer_project':
            if not self.partner_id:
                self.partner_id = self.project_id.partner_id
            if not self.sale_line_id:
                self.sale_line_id = self.project_id.sale_line_id

    def write(self, values):
        res = super(ProjectTask, self).write(values)
        # Done after super to avoid constraints on field recomputation
        if values.get('project_id'):
            project_dest = self.env['project.project'].browse(values['project_id'])
            if project_dest.bill_type == 'customer_project' and project_dest.pricing_type == 'employee_rate':
                self.write({'sale_line_id': False})
        if 'non_allow_billable' in values and self.filtered('allow_timesheets').sudo().timesheet_ids:
            timesheet_ids = self.filtered('allow_timesheets').timesheet_ids.filtered(
                lambda t: (not t.timesheet_invoice_id or t.timesheet_invoice_id.state == 'cancel')
            )
            if values['non_allow_billable']:
                timesheet_ids.write({'so_line': False})
                self.sale_line_id = False
            else:
                # We write project on timesheet lines to call _timesheet_preprocess. This function will set correct the SOL
                for project in timesheet_ids.project_id:
                    current_timesheet_ids = timesheet_ids.filtered(lambda t: t.project_id == project)
                    current_timesheet_ids.task_id.update({'sale_line_id': project.sale_line_id.id})
                    for employee in current_timesheet_ids.employee_id:
                        current_timesheet_ids.filtered(lambda t: t.employee_id == employee).write({'project_id': project.id})

        return res

    def _get_last_sol_of_customer(self):
        # Get the last SOL made for the customer in the current task where we need to compute
        self.ensure_one()
        if not self.commercial_partner_id or not self.allow_billable:
            return False
        domain = [('is_service', '=', True), ('order_partner_id', 'child_of', self.commercial_partner_id.id), ('is_expense', '=', False), ('state', 'in', ['sale', 'done'])]
        if self.project_id.bill_type == 'customer_project' and self.project_sale_order_id:
            domain.append(('order_id', '=?', self.project_sale_order_id.id))
        sale_lines = self.env['sale.order.line'].search(domain)
        for line in sale_lines:
            if line.remaining_hours_available and line.remaining_hours > 0:
                return line
        return False

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
                'default_product_id': self.timesheet_product_id.id or self.project_id.timesheet_product_id.id,
            },
        }

    def _get_timesheet(self):
        # return not invoiced timesheet and timesheet without so_line or so_line linked to task
        timesheet_ids = super(ProjectTask, self)._get_timesheet()
        return timesheet_ids.filtered(lambda t: (not t.timesheet_invoice_id or t.timesheet_invoice_id.state == 'cancel') and (not t.so_line or t.so_line == t.task_id._origin.sale_line_id))

    def _get_action_view_so_ids(self):
        return list(set((self.sale_order_id + self.timesheet_ids.so_line.order_id).ids))

class ProjectTaskRecurrence(models.Model):
    _inherit = 'project.task.recurrence'

    @api.model
    def _get_recurring_fields(self):
        return ['analytic_account_id'] + super(ProjectTaskRecurrence, self)._get_recurring_fields()
