# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
from odoo.tools import format_amount, float_round, float_is_zero
from odoo.tools.misc import formatLang


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

    pricing_type = fields.Selection([
        ('task_rate', 'Task rate'),
        ('fixed_rate', 'Project rate'),
        ('employee_rate', 'Employee rate')
    ], string="Pricing", default="task_rate",
        compute='_compute_pricing_type',
        search='_search_pricing_type',
        help='The task rate is perfect if you would like to bill different services to different customers at different rates. The fixed rate is perfect if you bill a service at a fixed rate per hour or day worked regardless of the employee who performed it. The employee rate is preferable if your employees deliver the same service at a different rate. For instance, junior and senior consultants would deliver the same service (= consultancy), but at a different rate because of their level of seniority.')
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
    partner_id = fields.Many2one(compute='_compute_partner_id', store=True, readonly=False)

    @api.depends('sale_line_id', 'sale_line_employee_ids', 'allow_billable')
    def _compute_pricing_type(self):
        billable_projects = self.filtered('allow_billable')
        for project in billable_projects:
            if project.sale_line_employee_ids:
                project.pricing_type = 'employee_rate'
            elif project.sale_line_id:
                project.pricing_type = 'fixed_rate'
            else:
                project.pricing_type = 'task_rate'
        (self - billable_projects).update({'pricing_type': False})

    def _search_pricing_type(self, operator, value):
        """ Search method for pricing_type field.

            This method returns a domain based on the operator and the value given in parameter:
            - operator = '=':
                - value = 'task_rate': [('sale_line_employee_ids', '=', False), ('sale_line_id', '=', False), ('allow_billable', '=', True)]
                - value = 'fixed_rate': [('sale_line_employee_ids', '=', False), ('sale_line_id', '!=', False), ('allow_billable', '=', True)]
                - value = 'employee_rate': [('sale_line_employee_ids', '!=', False), ('allow_billable', '=', True)]
                - value is False: [('allow_billable', '=', False)]
            - operator = '!=':
                - value = 'task_rate': ['|', ('sale_line_employee_ids', '!=', False), ('sale_line_id', '!=', False), ('allow_billable', '=', True)]
                - value = 'fixed_rate': ['|', ('sale_line_employee_ids', '!=', False), ('sale_line_id', '=', False), ('allow_billable', '=', True)]
                - value = 'employee_rate': [('sale_line_employee_ids', '=', False), ('allow_billable', '=', True)]
                - value is False: [('allow_billable', '!=', False)]

            :param operator: the supported operator is either '=' or '!='.
            :param value: the value than the field should be is among these values into the following tuple: (False, 'task_rate', 'fixed_rate', 'employee_rate').

            :returns: the domain to find the expected projects.
        """
        if operator not in ('=', '!='):
            raise UserError(_('Operation not supported'))
        if not ((isinstance(value, bool) and value is False) or (isinstance(value, str) and value in ('task_rate', 'fixed_rate', 'employee_rate'))):
            raise UserError(_('Value does not exist in the pricing type'))
        if value is False:
            return [('allow_billable', operator, value)]

        sol_cond = ('sale_line_id', '!=', False)
        mapping_cond = ('sale_line_employee_ids', '!=', False)
        if value == 'task_rate':
            domain = [expression.NOT_OPERATOR, sol_cond, expression.NOT_OPERATOR, mapping_cond]
        elif value == 'fixed_rate':
            domain = [sol_cond, expression.NOT_OPERATOR, mapping_cond]
        else:  # value == 'employee_rate'
            domain = [sol_cond, mapping_cond]

        domain = expression.normalize_domain(domain)
        if operator != '=':
            domain.insert(0, expression.NOT_OPERATOR)
        domain = expression.distribute_not(domain)
        domain = expression.AND([domain, [('allow_billable', '=', True)]])
        return domain

    @api.depends('partner_id', 'pricing_type')
    def _compute_display_create_order(self):
        for project in self:
            project.display_create_order = project.partner_id and project.pricing_type == 'task_rate'

    @api.depends('allow_timesheets', 'allow_billable')
    def _compute_timesheet_product_id(self):
        default_product = self.env.ref('sale_timesheet.time_product', False)
        for project in self:
            if not project.allow_timesheets or not project.allow_billable:
                project.timesheet_product_id = False
            elif not project.timesheet_product_id:
                project.timesheet_product_id = default_product

    @api.depends('pricing_type', 'allow_timesheets', 'allow_billable', 'sale_line_employee_ids', 'sale_line_employee_ids.employee_id')
    def _compute_warning_employee_rate(self):
        projects = self.filtered(lambda p: p.allow_billable and p.allow_timesheets and p.pricing_type == 'employee_rate')
        employees = self.env['account.analytic.line'].read_group([('task_id', 'in', projects.task_ids.ids)], ['employee_id', 'project_id'], ['employee_id', 'project_id'], ['employee_id', 'project_id'], lazy=False)
        dict_project_employee = defaultdict(list)
        for line in employees:
            dict_project_employee[line['project_id'][0]] += [line['employee_id'][0]] if line['employee_id'] else []
        for project in projects:
            project.warning_employee_rate = any(x not in project.sale_line_employee_ids.employee_id.ids for x in dict_project_employee[project.id])

        (self - projects).warning_employee_rate = False

    @api.depends('analytic_account_id', 'allow_billable', 'allow_timesheets')
    def _compute_project_overview(self):
        super()._compute_project_overview()
        for project in self.filtered(lambda p: not p.project_overview):
            project.project_overview = project.allow_billable or project.allow_timesheets

    @api.depends('sale_line_employee_ids.sale_line_id', 'sale_line_id')
    def _compute_partner_id(self):
        for project in self:
            if project.partner_id:
                continue
            if project.allow_billable and project.allow_timesheets and project.pricing_type != 'task_rate':
                sol = project.sale_line_id or project.sale_line_employee_ids.sale_line_id[:1]
                project.partner_id = sol.order_partner_id

    @api.depends('partner_id')
    def _compute_sale_line_id(self):
        super()._compute_sale_line_id()
        for project in self.filtered(lambda p: not p.sale_line_id and p.partner_id and p.pricing_type == 'employee_rate'):
            # Give a SOL by default either the last SOL with service product and remaining_hours > 0
            sol = self.env['sale.order.line'].search([
                ('is_service', '=', True),
                ('order_partner_id', 'child_of', project.partner_id.commercial_partner_id.id),
                ('is_expense', '=', False),
                ('state', 'in', ['sale', 'done']),
                ('remaining_hours', '>', 0)
            ], limit=1)
            project.sale_line_id = sol or project.sale_line_employee_ids.sale_line_id[:1]  # get the first SOL containing in the employee mappings if no sol found in the search

    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for project in self.filtered(lambda project: project.sale_line_id):
            if not project.sale_line_id.is_service:
                raise ValidationError(_("You cannot link a billable project to a sales order item that is not a service."))
            if project.sale_line_id.is_expense:
                raise ValidationError(_("You cannot link a billable project to a sales order item that comes from an expense or a vendor bill."))

    def write(self, values):
        res = super(Project, self).write(values)
        if 'allow_billable' in values and not values.get('allow_billable'):
            self.task_ids._get_timesheet().write({
                'so_line': False,
            })
        return res

    def _update_timesheets_sale_line_id(self):
        for project in self.filtered(lambda p: p.allow_billable and p.allow_timesheets):
            timesheet_ids = project.sudo(False).mapped('timesheet_ids').filtered(lambda t: not t.is_so_line_edited and t._is_not_billed())
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

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def get_panel_data(self):
        panel_data = super(Project, self).get_panel_data()
        return {
            **panel_data,
            'profitability_items': self._get_profitability_items()
        }

    def _get_profitability_items(self):
        if not self.user_has_groups('project.group_project_manager'):
            return {'data': []}
        profitability = self.get_profitability_common()
        data = []
        if self.allow_timesheets and self.user_has_groups('hr_timesheet.group_hr_timesheet_user'):
            data += [{
                'name': _("Timesheets"),
                'value': self.env.ref('sale_timesheet.project_profitability_timesheet_panel')._render({
                    'timesheet_unit_amount': float_round(profitability['timesheet_unit_amount'], precision_digits=2),
                    'timesheet_uom': self.env.company._timesheet_uom_text(),
                    'is_timesheet_uom_hour': self.env.company._is_timesheet_hour_uom(),
                    'percentage_billable': formatLang(self.env, profitability['timesheet_percentage_billable'], digits=0),
                }, engine='ir.qweb'),
            }]
        if self.allow_billable:
            margin_color = False
            if not float_is_zero(profitability['margin'], precision_digits=0):
                margin_color = profitability['margin'] > 0 and 'green' or 'red'
            data += [{
                'name': _("Revenues"),
                'value': format_amount(self.env, profitability['revenues'], self.env.company.currency_id)
            }, {
                'name': _("Costs"),
                'value': format_amount(self.env, profitability['costs'], self.env.company.currency_id)
            }, {
                'name': _("Margin"),
                'color': margin_color,
                'value': format_amount(self.env, profitability['margin'], self.env.company.currency_id)
            }]
        return {
            'action': self.allow_billable and self.allow_timesheets and "action_view_timesheet",
            'allow_billable': self.allow_billable,
            'data': data,
        }

    def get_profitability_common(self):
        self.ensure_one()
        profitability = self.env['project.profitability.report'].read_group(
            [('project_id', '=', self.id)],
            ['project_id',
             'timesheet_unit_amount',
             'amount_untaxed_to_invoice',
             'amount_untaxed_invoiced',
             'expense_amount_untaxed_to_invoice',
             'expense_amount_untaxed_invoiced',
             'other_revenues',
             'expense_cost',
             'timesheet_cost',
             'margin'],
            ['project_id'])
        timesheets = self.env['account.analytic.line'].read_group([('project_id', '=', self.id)], ['so_line', 'unit_amount'], ['so_line'])
        timesheet_billable = timesheet_non_billable = 0.0
        for timesheet in timesheets:
            if timesheet['so_line']:
                timesheet_billable += timesheet['unit_amount']
            else:
                timesheet_non_billable += timesheet['unit_amount']
        return {
            'costs': profitability and profitability[0]['timesheet_cost'] + profitability[0]['expense_cost'] or 0.0,
            'margin': profitability and profitability[0]['margin'] or 0.0,
            'revenues': profitability and (profitability[0]['amount_untaxed_invoiced'] + profitability[0]['amount_untaxed_to_invoice'] +
                                           profitability[0]['expense_amount_untaxed_invoiced'] + profitability[0]['expense_amount_untaxed_to_invoice'] +
                                           profitability[0]['other_revenues']) or 0.0,
            'timesheet_unit_amount': profitability and self._convert_project_uom_to_timesheet_encode_uom(profitability[0]['timesheet_unit_amount']) or 0.0,
            'timesheet_percentage_billable': timesheet_billable and timesheet_billable / (timesheet_billable + timesheet_non_billable) * 100 or 0.0,
        }

class ProjectTask(models.Model):
    _inherit = "project.task"

    def _get_default_partner_id(self, project, parent):
        res = super()._get_default_partner_id(project, parent)
        if not res and project:
            if project.pricing_type == 'employee_rate':
                return project.sale_line_employee_ids.sale_line_id.order_partner_id[:1]
        return res

    # override sale_order_id and make it computed stored field instead of regular field.
    sale_order_id = fields.Many2one(compute='_compute_sale_order_id', store=True, readonly=False,
    domain="['|', '|', ('partner_id', '=', partner_id), ('partner_id', 'child_of', commercial_partner_id), ('partner_id', 'parent_of', partner_id)]")
    analytic_account_id = fields.Many2one('account.analytic.account', related='sale_order_id.analytic_account_id')
    pricing_type = fields.Selection(related="project_id.pricing_type")
    sale_line_id = fields.Many2one(domain="[('company_id', '=', company_id), ('is_service', '=', True), ('order_partner_id', 'child_of', commercial_partner_id), ('is_expense', '=', False), ('state', 'in', ['sale', 'done']), '|', ('project_id.pricing_type', '=', 'task_rate'), ('order_id', '=?', project_sale_order_id)]")
    is_project_map_empty = fields.Boolean("Is Project map empty", compute='_compute_is_project_map_empty')
    has_multi_sol = fields.Boolean(compute='_compute_has_multi_sol', compute_sudo=True)
    allow_billable = fields.Boolean(related="project_id.allow_billable")
    timesheet_product_id = fields.Many2one(related="project_id.timesheet_product_id")
    remaining_hours_so = fields.Float('Remaining Hours on SO', compute='_compute_remaining_hours_so', compute_sudo=True)
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
                mapped_remaining_hours[timesheet.task_id._origin.id] += timesheet.product_uom_id._compute_quantity(delta, uom_hour)

        for task in self:
            task.remaining_hours_so = mapped_remaining_hours[task._origin.id]

    @api.depends('analytic_account_id.active')
    def _compute_analytic_account_active(self):
        super()._compute_analytic_account_active()
        for task in self:
            task.analytic_account_active = task.analytic_account_active or task.analytic_account_id.active

    @api.depends('sale_line_id', 'project_id', 'allow_billable', 'commercial_partner_id')
    def _compute_sale_order_id(self):
        for task in self:
            if not task.allow_billable:
                task.sale_order_id = False
            else:
                if task.sale_line_id:
                    task.sale_order_id = task.sale_line_id.sudo().order_id
                elif task.project_id.sale_order_id:
                    task.sale_order_id = task.project_id.sale_order_id
                if task.commercial_partner_id != task.sale_order_id.partner_id.commercial_partner_id:
                    task.sale_order_id = False
                if task.sale_order_id and not task.partner_id:
                    task.partner_id = task.sale_order_id.partner_id

    @api.depends('commercial_partner_id', 'sale_line_id.order_partner_id.commercial_partner_id', 'parent_id.sale_line_id', 'project_id.sale_line_id', 'allow_billable')
    def _compute_sale_line(self):
        billable_tasks = self.filtered('allow_billable')
        (self - billable_tasks).update({'sale_line_id': False})
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

    def _get_last_sol_of_customer(self):
        # Get the last SOL made for the customer in the current task where we need to compute
        self.ensure_one()
        if not self.commercial_partner_id or not self.allow_billable:
            return False
        domain = [('company_id', '=', self.company_id.id), ('is_service', '=', True), ('order_partner_id', 'child_of', self.commercial_partner_id.id), ('is_expense', '=', False), ('state', 'in', ['sale', 'done']), ('remaining_hours', '>', 0)]
        if self.project_id.pricing_type != 'task_rate' and self.project_sale_order_id and self.commercial_partner_id == self.project_id.partner_id.commercial_partner_id:
            domain.append(('order_id', '=?', self.project_sale_order_id.id))
        return self.env['sale.order.line'].search(domain, limit=1)

    def _get_timesheet(self):
        # return not invoiced timesheet and timesheet without so_line or so_line linked to task
        timesheet_ids = super(ProjectTask, self)._get_timesheet()
        return timesheet_ids.filtered(lambda t: t._is_not_billed())

    def _get_action_view_so_ids(self):
        return list(set((self.sale_order_id + self.timesheet_ids.so_line.order_id).ids))

class ProjectTaskRecurrence(models.Model):
    _inherit = 'project.task.recurrence'

    @api.model
    def _get_recurring_fields(self):
        return ['analytic_account_id'] + super(ProjectTaskRecurrence, self)._get_recurring_fields()
