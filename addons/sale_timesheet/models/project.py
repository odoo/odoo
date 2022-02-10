# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
from odoo.tools import format_amount, float_is_zero, formatLang

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
    billable_percentage = fields.Integer(
        compute='_compute_billable_percentage',
        help="% of timesheets that are billable compared to the total number of timesheets linked to the AA of the project, rounded to the unit.")
    display_create_order = fields.Boolean(compute='_compute_display_create_order')
    timesheet_product_id = fields.Many2one(
        'product.product', string='Timesheet Product',
        domain="""[
            ('detailed_type', '=', 'service'),
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
                - value = 'task_rate': ['|', '|', ('sale_line_employee_ids', '!=', False), ('sale_line_id', '!=', False), ('allow_billable', '=', False)]
                - value = 'fixed_rate': ['|', '|', ('sale_line_employee_ids', '!=', False), ('sale_line_id', '=', False), ('allow_billable', '=', False)]
                - value = 'employee_rate': ['|', ('sale_line_employee_ids', '=', False), ('allow_billable', '=', False)]
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
            domain = [mapping_cond]

        domain = expression.AND([domain, [('allow_billable', '=', True)]])
        domain = expression.normalize_domain(domain)
        if operator != '=':
            domain.insert(0, expression.NOT_OPERATOR)
        domain = expression.distribute_not(domain)
        return domain

    @api.depends('analytic_account_id', 'timesheet_ids')
    def _compute_billable_percentage(self):
        timesheets_read_group = self.env['account.analytic.line'].read_group([('project_id', 'in', self.ids)], ['project_id', 'so_line', 'unit_amount'], ['project_id', 'so_line'], lazy=False)
        timesheets_by_project = defaultdict(list)
        for res in timesheets_read_group:
            timesheets_by_project[res['project_id'][0]].append((res['unit_amount'], bool(res['so_line'])))
        for project in self:
            timesheet_total = timesheet_billable = 0.0
            for unit_amount, is_billable_timesheet in timesheets_by_project[project.id]:
                timesheet_total += unit_amount
                if is_billable_timesheet:
                    timesheet_billable += unit_amount
            billable_percentage = timesheet_billable / timesheet_total * 100 if timesheet_total > 0 else 0
            project.billable_percentage = round(billable_percentage)

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

    def action_open_project_invoices(self):
        invoices = self.env['account.move'].search([
            ('line_ids.analytic_account_id', '!=', False),
            ('line_ids.analytic_account_id', 'in', self.analytic_account_id.ids),
            ('move_type', '=', 'out_invoice')
        ])
        action = {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', invoices.ids)],
            'context': {
                'create': False,
            }
        }
        if len(invoices) == 1:
            action['views'] = [[False, 'form']]
            action['res_id'] = invoices.id
        return action

    def action_view_timesheet(self):
        self.ensure_one()
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

    def action_billable_time_button(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_timesheet.timesheet_action_all")
        action.update({
            'context': {
                'search_default_groupby_task': True,
                'default_project_id': self.id,
            },
            'domain': [('project_id', '=', self.id)],
            'view_mode': 'tree,kanban,pivot,graph,form',
            'views': [
                [self.env.ref('hr_timesheet.timesheet_view_tree_user').id, 'tree'],
                [self.env.ref('hr_timesheet.view_kanban_account_analytic_line').id, 'kanban'],
                [self.env.ref('hr_timesheet.view_hr_timesheet_line_pivot').id, 'pivot'],
                [self.env.ref('hr_timesheet.view_hr_timesheet_line_graph_all').id, 'graph'],
                [self.env.ref('hr_timesheet.timesheet_view_form_user').id, 'form'],
            ],
        })
        return action

    def action_view_all_rating(self):
        return {
            'name': _('Rating'),
            'type': 'ir.actions.act_window',
            'res_model': 'rating.rating',
            'view_mode': 'kanban,list,graph,pivot,form',
            'view_type': 'ir.actions.act_window',
            'context': {
                'search_default_rating_last_30_days': True,
            },
            'domain': [('consumed','=',True), ('parent_res_model','=','project.project'), ('parent_res_id', '=', self.id)],
        }

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def get_panel_data(self):
        panel_data = super(Project, self).get_panel_data()
        return {
            **panel_data,
            'analytic_account_id': self.analytic_account_id.id,
            'sold_items': self._get_sold_items(),
            'profitability_items': self._get_profitability_items(),
        }

    def _get_sale_order_lines(self):
        sale_orders = self.sale_order_id | self.tasks.sale_order_id
        return self.env['sale.order.line'].search([('order_id', 'in', sale_orders.ids), ('is_service', '=', True), ('is_downpayment', '=', False)], order='id asc')

    def _get_sold_items(self):
        sols = self._get_sale_order_lines()
        number_sale_orders = len(sols.order_id)
        sold_items = {
            'allow_billable': self.allow_billable,
            'data': [],
            'number_sols': len(sols),
            'total_sold': 0,
            'effective_sold': 0,
            'company_unit_name': self.env.company.timesheet_encode_uom_id.name
        }
        product_uom_unit = self.env.ref('uom.product_uom_unit')
        for sol in sols:
            name = [x[1] for x in sol.name_get()] if number_sale_orders > 1 else sol.name
            qty_delivered = sol.product_uom._compute_quantity(sol.qty_delivered, self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
            product_uom_qty = sol.product_uom._compute_quantity(sol.product_uom_qty, self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
            if qty_delivered > 0 or product_uom_qty > 0:
                sold_items['data'].append({
                    'name': name,
                    'value': '%s / %s %s' % (formatLang(self.env, qty_delivered, 1), formatLang(self.env, product_uom_qty, 1), sol.product_uom.name if sol.product_uom == product_uom_unit else self.env.company.timesheet_encode_uom_id.name),
                    'color': 'red' if qty_delivered > product_uom_qty else 'black'
                })
                #We only want to consider hours and days for this calculation, and eventually units if the service policy is not based on milestones
                if sol.product_uom.category_id == self.env.company.timesheet_encode_uom_id.category_id or (sol.product_uom == product_uom_unit and sol.product_id.service_policy != 'delivered_manual'):
                    sold_items['total_sold'] += product_uom_qty
                    sold_items['effective_sold'] += qty_delivered
        remaining = sold_items['total_sold'] - sold_items['effective_sold']
        sold_items['remaining'] = {
            'value': remaining,
            'color': 'red' if remaining < 0 else 'black',
        }
        return sold_items

    def _get_profitability_items(self):
        if not self.user_has_groups('project.group_project_manager'):
            return {'data': []}
        data = []
        if self.allow_billable:
            profitability = self._get_profitability_common()
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

    def _get_profitability_common(self):
        self.ensure_one()
        result = {
            'costs': 0.0,
            'margin': 0.0,
            'revenues': 0.0
        }

        profitability = self.env['project.profitability.report'].read_group(
            [('project_id', '=', self.id)],
            ['project_id',
                'amount_untaxed_to_invoice',
                'amount_untaxed_invoiced',
                'expense_amount_untaxed_to_invoice',
                'expense_amount_untaxed_invoiced',
                'other_revenues',
                'expense_cost',
                'timesheet_cost',
                'margin'],
            ['project_id'], limit=1)
        if profitability:
            profitability = profitability[0]
            result.update({
                'costs': profitability['timesheet_cost'] + profitability['expense_cost'],
                'margin': profitability['margin'],
                'revenues': (profitability['amount_untaxed_invoiced'] + profitability['amount_untaxed_to_invoice'] +
                                profitability['expense_amount_untaxed_invoiced'] + profitability['expense_amount_untaxed_to_invoice'] +
                                profitability['other_revenues']),
            })
        return result

    def _get_sale_order_stat_button(self):
        so_button = super()._get_sale_order_stat_button()
        so_button['show'] &= self.allow_billable
        return so_button

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            buttons.append({
                'icon': 'clock-o',
                'text': _('Billable Time'),
                'number': '%s %%' % (self.billable_percentage),
                'action_type': 'object',
                'action': 'action_billable_time_button',
                'additional_context': json.dumps({
                    'active_id': self.id,
                    'default_project_id': self.id
                }),
                'show': self.allow_timesheets and bool(self.analytic_account_id),
                'sequence': 9,
            })
        return buttons

class ProjectTask(models.Model):
    _inherit = "project.task"

    def _get_default_partner_id(self, project, parent):
        res = super()._get_default_partner_id(project, parent)
        if not res and project:
            # project in sudo if the current user is a portal user.
            related_project = project if not self.user_has_groups('!base.group_user,base.group_portal') else project.sudo()
            if related_project.pricing_type == 'employee_rate':
                return related_project.sale_line_employee_ids.sale_line_id.order_partner_id[:1]
        return res

    sale_order_id = fields.Many2one(domain="['|', '|', ('partner_id', '=', partner_id), ('partner_id', 'child_of', commercial_partner_id), ('partner_id', 'parent_of', partner_id)]")
    so_analytic_account_id = fields.Many2one(related='sale_order_id.analytic_account_id', string='Sale Order Analytic Account')
    pricing_type = fields.Selection(related="project_id.pricing_type")
    is_project_map_empty = fields.Boolean("Is Project map empty", compute='_compute_is_project_map_empty')
    has_multi_sol = fields.Boolean(compute='_compute_has_multi_sol', compute_sudo=True)
    allow_billable = fields.Boolean(related="project_id.allow_billable")
    timesheet_product_id = fields.Many2one(related="project_id.timesheet_product_id")
    remaining_hours_so = fields.Float('Remaining Hours on SO', compute='_compute_remaining_hours_so', compute_sudo=True)
    remaining_hours_available = fields.Boolean(related="sale_line_id.remaining_hours_available")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {
            'allow_billable',
            'remaining_hours_available',
            'remaining_hours_so',
        }

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

    @api.depends('so_analytic_account_id.active')
    def _compute_analytic_account_active(self):
        super()._compute_analytic_account_active()
        for task in self:
            task.analytic_account_active = task.analytic_account_active or task.so_analytic_account_id.active

    @api.depends('allow_billable')
    def _compute_sale_order_id(self):
        billable_tasks = self.filtered('allow_billable')
        super(ProjectTask, billable_tasks)._compute_sale_order_id()
        (self - billable_tasks).sale_order_id = False

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
        return ['so_analytic_account_id'] + super(ProjectTaskRecurrence, self)._get_recurring_fields()
