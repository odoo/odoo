# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import SQL
from odoo.exceptions import ValidationError, UserError
from odoo.tools.translate import _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model
    def default_get(self, fields):
        """ Pre-fill timesheet product as "Time" data product when creating new project allowing billable tasks by default. """
        result = super().default_get(fields)
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
    sale_line_employee_ids = fields.One2many('project.sale.line.employee.map', 'project_id', copy=False, export_string_translation=False,
        string="Sales order item that will be selected by default on the timesheets of the corresponding employee. It bypasses the sales order item defined on the project and the task, and can be modified on each timesheet entry if necessary. In other words, it defines the rate at which an employee's time is billed based on their expertise, skills or experience, for instance.\n"
             "If you would like to bill the same service at a different rate, you need to create two separate sales order items as each sales order item can only have a single unit price at a time.\n"
             "You can also define the hourly company cost of your employees for their timesheets on this project specifically. It will bypass the timesheet cost set on the employee.")
    timesheet_product_id = fields.Many2one(
        'product.product', string='Timesheet Product',
        domain="""[
            ('type', '=', 'service'),
            ('invoice_policy', '=', 'delivery'),
            ('service_type', '=', 'timesheet'),
        ]""",
        help='Service that will be used by default when invoicing the time spent on a task. It can be modified on each task individually by selecting a specific sales order item.',
        check_company=True,
        compute="_compute_timesheet_product_id", store=True, readonly=False,
        default=_default_timesheet_product_id)
    warning_employee_rate = fields.Boolean(compute='_compute_warning_employee_rate', compute_sudo=True, export_string_translation=False)
    partner_id = fields.Many2one(
        compute='_compute_partner_id', store=True, readonly=False)
    allocated_hours = fields.Float(copy=False)
    billing_type = fields.Selection(
        compute="_compute_billing_type",
        selection=[
            ('not_billable', 'not billable'),
            ('manually', 'billed manually'),
        ],
        default='not_billable',
        required=True,
        readonly=False,
        store=True,
    )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form' and self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day'):
            for node in arch.xpath("//field[@name='display_cost'][not(@string)]"):
                node.set('string', 'Daily Cost')
        return arch, view

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
        employees = self.env['account.analytic.line']._read_group(
            [('task_id', 'in', projects.task_ids.ids), ('employee_id', '!=', False)],
            ['project_id'],
            ['employee_id:array_agg'],
        )
        dict_project_employee = {project.id: employee_ids for project, employee_ids in employees}
        for project in projects:
            project.warning_employee_rate = any(
                x not in project.sale_line_employee_ids.employee_id.ids
                for x in dict_project_employee.get(project.id, ())
            )

        (self - projects).warning_employee_rate = False

    @api.depends('sale_line_employee_ids.sale_line_id', 'sale_line_id')
    def _compute_partner_id(self):
        billable_projects = self.filtered('allow_billable')
        for project in billable_projects:
            if project.partner_id:
                continue
            if project.allow_billable and project.allow_timesheets and project.pricing_type != 'task_rate':
                sol = project.sale_line_id or project.sale_line_employee_ids.sale_line_id[:1]
                project.partner_id = sol.order_partner_id
        super(ProjectProject, self - billable_projects)._compute_partner_id()

    @api.depends('partner_id')
    def _compute_sale_line_id(self):
        super()._compute_sale_line_id()
        for project in self.filtered(lambda p: not p.sale_line_id and p.partner_id and p.pricing_type == 'employee_rate'):
            # Give a SOL by default either the last SOL with service product and remaining_hours > 0
            SaleOrderLine = self.env['sale.order.line']
            sol = SaleOrderLine.search(expression.AND([
                SaleOrderLine._domain_sale_line_service(),
                [('order_partner_id', 'child_of', project.partner_id.commercial_partner_id.id), ('remaining_hours', '>', 0)],
            ]), limit=1)
            project.sale_line_id = sol or project.sale_line_employee_ids.sale_line_id[:1]  # get the first SOL containing in the employee mappings if no sol found in the search

    @api.depends('sale_line_employee_ids.sale_line_id', 'allow_billable')
    def _compute_sale_order_count(self):
        billable_projects = self.filtered('allow_billable')
        super(ProjectProject, billable_projects)._compute_sale_order_count()
        non_billable_projects = self - billable_projects
        non_billable_projects.sale_order_line_count = 0
        non_billable_projects.sale_order_count = 0

    @api.depends('allow_billable', 'allow_timesheets')
    def _compute_billing_type(self):
        self.filtered(lambda project: (not project.allow_billable or not project.allow_timesheets) and project.billing_type == 'manually').billing_type = 'not_billable'

    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for project in self.filtered(lambda project: project.sale_line_id):
            if not project.sale_line_id.is_service:
                raise ValidationError(_("You cannot link a billable project to a sales order item that is not a service."))
            if project.sale_line_id.is_expense:
                raise ValidationError(_("You cannot link a billable project to a sales order item that comes from an expense or a vendor bill."))

    def write(self, values):
        res = super().write(values)
        if 'allow_billable' in values and not values.get('allow_billable'):
            self.task_ids._get_timesheet().write({
                'so_line': False,
            })
        return res

    def _update_timesheets_sale_line_id(self):
        for project in self.filtered(lambda p: p.allow_billable and p.allow_timesheets):
            timesheet_ids = project.mapped('timesheet_ids').filtered(lambda t: not t.is_so_line_edited and t._is_updatable_timesheet())
            if not timesheet_ids:
                continue
            for employee_id in project.sale_line_employee_ids.filtered(lambda l: l.project_id == project).employee_id:
                sale_line_id = project.sale_line_employee_ids.filtered(lambda l: l.project_id == project and l.employee_id == employee_id).sale_line_id
                timesheet_ids.filtered(lambda t: t.employee_id == employee_id).sudo().so_line = sale_line_id

    def action_view_timesheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheets of %s', self.name),
            'domain': [('project_id', '!=', False)],
            'res_model': 'account.analytic.line',
            'view_id': False,
            'view_mode': 'list,form',
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

    def action_billable_time_button(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_timesheet.timesheet_action_from_sales_order_item")
        action.update({
            'context': {
                'search_default_groupby_timesheet_invoice_type': True,
                'default_project_id': self.id,
            },
            'domain': [('project_id', '=', self.id)],
        })
        return action

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        self.ensure_one()
        if section_name in ['billable_fixed', 'billable_time', 'billable_milestones', 'billable_manual', 'non_billable']:
            action = self.action_billable_time_button()
            if domain:
                action['domain'] = expression.AND([[('project_id', '=', self.id)], domain])
            action['context'].update(search_default_groupby_timesheet_invoice_type=False, **self.env.context)
            graph_view = False
            if section_name == 'billable_time':
                graph_view = self.env.ref('sale_timesheet.view_hr_timesheet_line_graph_invoice_employee').id
            action['views'] = [
                (view_id, view_type) if view_type != 'graph' else (graph_view or view_id, view_type)
                for view_id, view_type in action['views']
            ]
            if res_id:
                if 'views' in action:
                    action['views'] = [
                        (view_id, view_type)
                        for view_id, view_type in action['views']
                        if view_type == 'form'
                    ] or [False, 'form']
                action['view_mode'] = 'form'
                action['res_id'] = res_id
            return action
        return super().action_profitability_items(section_name, domain, res_id)

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def get_panel_data(self):
        panel_data = super().get_panel_data()
        return {
            **panel_data,
            'account_id': self.account_id.id,
        }

    def _get_foldable_section(self):
        foldable_section = super()._get_foldable_section()
        return foldable_section + [
            'billable_fixed',
            'billable_milestones',
            'billable_time',
            'billable_manual',
        ]

    def _get_sale_order_items_query(self, domain_per_model=None):
        if domain_per_model is None:
            domain_per_model = {'project.task': [('allow_billable', '=', True)]}
        else:
            domain_per_model['project.task'] = expression.AND([
                domain_per_model.get('project.task', []),
                [('allow_billable', '=', True)],
            ])
        query = super()._get_sale_order_items_query(domain_per_model)

        Timesheet = self.env['account.analytic.line']
        timesheet_domain = [('project_id', 'in', self.ids), ('so_line', '!=', False), ('project_id.allow_billable', '=', True)]
        if Timesheet._name in domain_per_model:
            timesheet_domain = expression.AND([
                domain_per_model.get(Timesheet._name, []),
                timesheet_domain,
            ])
        timesheet_query = Timesheet._where_calc(timesheet_domain)
        Timesheet._apply_ir_rules(timesheet_query, 'read')
        timesheet_sql = timesheet_query.select(
            f'{Timesheet._table}.project_id AS id',
            f'{Timesheet._table}.so_line AS sale_line_id',
        )

        EmployeeMapping = self.env['project.sale.line.employee.map']
        employee_mapping_domain = [('project_id', 'in', self.ids), ('project_id.allow_billable', '=', True), ('sale_line_id', '!=', False)]
        if EmployeeMapping._name in domain_per_model:
            employee_mapping_domain = expression.AND([
                domain_per_model[EmployeeMapping._name],
                employee_mapping_domain,
            ])
        employee_mapping_query = EmployeeMapping._where_calc(employee_mapping_domain)
        EmployeeMapping._apply_ir_rules(employee_mapping_query, 'read')
        employee_mapping_sql = employee_mapping_query.select(
            f'{EmployeeMapping._table}.project_id AS id',
            f'{EmployeeMapping._table}.sale_line_id',
        )

        query._tables['project_sale_order_item'] = SQL('(%s)', SQL(' UNION ').join([
            query._tables['project_sale_order_item'],
            timesheet_sql,
            employee_mapping_sql,
        ]))
        return query

    def _get_domain_from_section_id(self, section_id):
        section_domains = {
            'materials': [
                ('product_id.type', '!=', 'service')
            ],
            'billable_fixed': [
                ('product_id.type', '=', 'service'),
                ('product_id.invoice_policy', '=', 'order')
            ],
            'billable_milestones': [
                ('product_id.type', '=', 'service'),
                ('product_id.invoice_policy', '=', 'delivery'),
                ('product_id.service_type', '=', 'milestones'),
            ],
            'billable_time': [
                ('product_id.type', '=', 'service'),
                ('product_id.invoice_policy', '=', 'delivery'),
                ('product_id.service_type', '=', 'timesheet'),
            ],
            'billable_manual': [
                ('product_id.type', '=', 'service'),
                ('product_id.invoice_policy', '=', 'delivery'),
                ('product_id.service_type', '=', 'manual'),
            ],
        }

        return self._get_sale_items_domain(section_domains.get(section_id, []))

    def _get_profitability_labels(self):
        return {
            **super()._get_profitability_labels(),
            'billable_fixed': self.env._('Timesheets (Fixed Price)'),
            'billable_time': self.env._('Timesheets (Billed on Timesheets)'),
            'billable_milestones': self.env._('Timesheets (Billed on Milestones)'),
            'billable_manual': self.env._('Timesheets (Billed Manually)'),
            'non_billable': self.env._('Timesheets (Non-Billable)'),
            'timesheet_revenues': self.env._('Timesheets revenues'),
            'other_costs': self.env._('Materials'),
        }

    def _get_profitability_sequence_per_invoice_type(self):
        return {
            **super()._get_profitability_sequence_per_invoice_type(),
            'billable_fixed': 1,
            'billable_time': 2,
            'billable_milestones': 3,
            'billable_manual': 4,
            'non_billable': 5,
            'timesheet_revenues': 6,
            'other_costs': 12,
        }

    def _get_profitability_aal_domain(self):
        domain = ['|', ('project_id', 'in', self.ids), ('so_line', 'in', self._fetch_sale_order_item_ids())]
        return expression.AND([
            super()._get_profitability_aal_domain(),
            domain,
        ])

    def _get_profitability_items_from_aal(self, profitability_items, with_action=True):
        if not self.allow_timesheets:
            total_invoiced = total_to_invoice = 0.0
            revenue_data = []
            for revenue in profitability_items['revenues']['data']:
                if revenue['id'] in ['billable_fixed', 'billable_time', 'billable_milestones', 'billable_manual']:
                    continue
                total_invoiced += revenue['invoiced']
                total_to_invoice += revenue['to_invoice']
                revenue_data.append(revenue)
            profitability_items['revenues'] = {
                'data': revenue_data,
                'total': {'to_invoice': total_to_invoice, 'invoiced': total_invoiced},
            }
            return profitability_items
        aa_line_read_group = self.env['account.analytic.line'].sudo()._read_group(
            self.sudo()._get_profitability_aal_domain(),
            ['timesheet_invoice_type', 'timesheet_invoice_id', 'currency_id'],
            ['amount:sum', 'id:array_agg'],
        )
        can_see_timesheets = with_action and len(self) == 1 and self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver')
        revenues_dict = {}
        costs_dict = {}
        total_revenues = {'invoiced': 0.0, 'to_invoice': 0.0}
        total_costs = {'billed': 0.0, 'to_bill': 0.0}
        convert_company = self.company_id or self.env.company
        for timesheet_invoice_type, dummy, currency, amount, ids in aa_line_read_group:
            amount = currency._convert(amount, self.currency_id, convert_company)
            invoice_type = timesheet_invoice_type
            cost = costs_dict.setdefault(invoice_type, {'billed': 0.0, 'to_bill': 0.0})
            revenue = revenues_dict.setdefault(invoice_type, {'invoiced': 0.0, 'to_invoice': 0.0})
            if amount < 0:  # cost
                cost['billed'] += amount
                total_costs['billed'] += amount
            else:  # revenues
                revenue['invoiced'] += amount
                total_revenues['invoiced'] += amount
            if can_see_timesheets and invoice_type not in ['other_costs', 'other_revenues']:
                cost.setdefault('record_ids', []).extend(ids)
                revenue.setdefault('record_ids', []).extend(ids)
        action_name = None
        if can_see_timesheets:
            action_name = 'action_profitability_items'

        def get_timesheets_action(invoice_type, record_ids):
            args = [invoice_type, [('id', 'in', record_ids)]]
            if len(record_ids) == 1:
                args.append(record_ids[0])
            return {'name': action_name, 'type': 'object', 'args': json.dumps(args)}

        sequence_per_invoice_type = self._get_profitability_sequence_per_invoice_type()

        def convert_dict_into_profitability_data(d, cost=True):
            profitability_data = []
            key1, key2 = ['to_bill', 'billed'] if cost else ['to_invoice', 'invoiced']
            for invoice_type, vals in d.items():
                if not vals[key1] and not vals[key2]:
                    continue
                record_ids = vals.pop('record_ids', [])
                data = {'id': invoice_type, 'sequence': sequence_per_invoice_type[invoice_type], **vals}
                if record_ids:
                    if invoice_type not in ['other_costs', 'other_revenues'] and can_see_timesheets:  # action to see the timesheets
                        action = get_timesheets_action(invoice_type, record_ids)
                        data['action'] = action
                profitability_data.append(data)
            return profitability_data

        def merge_profitability_data(a, b):
            return {
                'data': a['data'] + b['data'],
                'total': {key: a['total'][key] + b['total'][key] for key in a['total'] if key in b['total']}
            }

        for revenue in profitability_items['revenues']['data']:
            revenue_id = revenue['id']
            aal_revenue = revenues_dict.pop(revenue_id, {})
            revenue['to_invoice'] += aal_revenue.get('to_invoice', 0.0)
            revenue['invoiced'] += aal_revenue.get('invoiced', 0.0)
            record_ids = aal_revenue.get('record_ids', [])
            if can_see_timesheets and record_ids:
                action = get_timesheets_action(revenue_id, record_ids)
                revenue['action'] = action

        for cost in profitability_items['costs']['data']:
            cost_id = cost['id']
            aal_cost = costs_dict.pop(cost_id, {})
            cost['to_bill'] += aal_cost.get('to_bill', 0.0)
            cost['billed'] += aal_cost.get('billed', 0.0)
            record_ids = aal_cost.get('record_ids', [])
            if can_see_timesheets and record_ids:
                cost['action'] = get_timesheets_action(cost_id, record_ids)

        profitability_items['revenues'] = merge_profitability_data(
            profitability_items['revenues'],
            {'data': convert_dict_into_profitability_data(revenues_dict, False), 'total': total_revenues},
        )
        profitability_items['costs'] = merge_profitability_data(
            profitability_items['costs'],
            {'data': convert_dict_into_profitability_data(costs_dict), 'total': total_costs},
        )
        return profitability_items

    def _get_domain_aal_with_no_move_line(self):
        # we add the tuple 'project_id = False' in the domain to remove the timesheets from the search.
        return expression.AND([
            super()._get_domain_aal_with_no_move_line(),
            [('project_id', '=', False)]
        ])

    def _get_service_policy_to_invoice_type(self):
        return {
            **super()._get_service_policy_to_invoice_type(),
            'ordered_prepaid': 'billable_fixed',
            'delivered_milestones': 'billable_milestones',
            'delivered_timesheet': 'billable_time',
            'delivered_manual': 'billable_manual',
        }

    def _get_profitability_items(self, with_action=True):
        return self._get_profitability_items_from_aal(
            super()._get_profitability_items(with_action),
            with_action
        )
