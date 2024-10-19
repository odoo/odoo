# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from collections import defaultdict

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.osv.expression import AND, NEGATIVE_TERM_OPERATORS, TERM_OPERATORS_NEGATION
from odoo.addons.project.models.project_task import CLOSED_STATES


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tasks_ids = fields.Many2many('project.task', compute='_compute_tasks_ids', search='_search_tasks_ids', string='Tasks associated with this sale', export_string_translation=False)
    tasks_count = fields.Integer(string='Tasks', compute='_compute_tasks_ids', groups="project.group_project_user", export_string_translation=False)

    visible_project = fields.Boolean('Display project', compute='_compute_visible_project', readonly=True, export_string_translation=False)
    project_ids = fields.Many2many('project.project', compute="_compute_project_ids", string='Projects', copy=False, groups="project.group_project_user,project.group_project_milestone", export_string_translation=False)
    project_count = fields.Integer(string='Number of Projects', compute='_compute_project_ids', groups='project.group_project_user', export_string_translation=False)
    milestone_count = fields.Integer(compute='_compute_milestone_count', export_string_translation=False)
    is_product_milestone = fields.Boolean(compute='_compute_is_product_milestone', export_string_translation=False)
    show_create_project_button = fields.Boolean(compute='_compute_show_project_and_task_button', groups='project.group_project_user', export_string_translation=False)
    show_project_button = fields.Boolean(compute='_compute_show_project_and_task_button', groups='project.group_project_user', export_string_translation=False)
    show_task_button = fields.Boolean(compute='_compute_show_project_and_task_button', groups='project.group_project_user', export_string_translation=False)
    closed_task_count = fields.Integer(compute='_compute_tasks_ids', export_string_translation=False)
    completed_task_percentage = fields.Float(compute="_compute_completed_task_percentage", export_string_translation=False)
    project_id = fields.Many2one('project.project', domain=[('allow_billable', '=', True)], help="A task will be created for the project upon sales order confirmation. The analytic distribution of this project will also serve as a reference for newly created sales order items.")
    project_account_id = fields.Many2one('account.analytic.account', related='project_id.account_id')

    def _compute_milestone_count(self):
        read_group = self.env['project.milestone']._read_group(
            [('sale_line_id', 'in', self.order_line.ids)],
            ['sale_line_id'],
            ['__count'],
        )
        line_data = {sale_line.id: count for sale_line, count in read_group}
        for order in self:
            order.milestone_count = sum(line_data.get(line.id, 0) for line in order.order_line)

    def _compute_is_product_milestone(self):
        for order in self:
            order.is_product_milestone = order.order_line.product_id.filtered(lambda p: p.service_policy == 'delivered_milestones')

    def _compute_show_project_and_task_button(self):
        is_project_manager = self.env.user.has_group('project.group_project_manager')
        show_button_ids = self.env['sale.order.line']._read_group([
            ('order_id', 'in', self.ids),
            ('order_id.state', 'not in', ['draft', 'sent']),
            ('product_id.type', '=', 'service'),
        ], aggregates=['order_id:array_agg'])[0][0]
        for order in self:
            order.show_project_button = order.id in show_button_ids and order.project_count
            order.show_task_button = order.show_project_button or order.tasks_count
            order.show_create_project_button = (
                is_project_manager
                and order.id in show_button_ids
                and not order.project_count
            )

    @api.model
    def _search_tasks_ids(self, operator, value):
        if operator in NEGATIVE_TERM_OPERATORS:
            positive_operator = TERM_OPERATORS_NEGATION[operator]
        else:
            positive_operator = operator
        task_domain = [('display_name' if isinstance(value, str) else 'id', positive_operator, value), ('sale_order_id', '!=', False)]
        query = self.env['project.task']._search(task_domain)
        return [('id', 'in' if positive_operator == operator else 'not in', query.subselect('sale_order_id'))]

    @api.depends('order_line.product_id.project_id')
    def _compute_tasks_ids(self):
        tasks_per_so = self.env['project.task']._read_group(
            domain=['&', ('project_id', '!=', False), '|', ('sale_line_id', 'in', self.order_line.ids), ('sale_order_id', 'in', self.ids)],
            groupby=['sale_order_id', 'state'],
            aggregates=['id:recordset', '__count']
        )
        so_with_tasks = self.env['sale.order']
        for order, state, tasks_ids, tasks_count in tasks_per_so:
            if order:
                order.tasks_ids += tasks_ids
                order.tasks_count += tasks_count
                order.closed_task_count += state in CLOSED_STATES and tasks_count
                so_with_tasks += order
            else:
                # tasks that have no sale_order_id need to be associated with the SO from their sale_line_id
                for task in tasks_ids:
                    task_so = task.sale_line_id.order_id
                    task_so.tasks_ids = [Command.link(task.id)]
                    task_so.tasks_count += 1
                    task_so.closed_task_count += state in CLOSED_STATES
                    so_with_tasks += task_so
        remaining_orders = self - so_with_tasks
        if remaining_orders:
            remaining_orders.tasks_ids = [Command.clear()]
            remaining_orders.tasks_count = 0
            remaining_orders.closed_task_count = 0

    @api.depends('order_line.product_id.service_tracking')
    def _compute_visible_project(self):
        """ Users should be able to select a project_id on the SO if at least one SO line has a product with its service tracking
        configured as 'task_in_project' """
        for order in self:
            order.visible_project = any(
                service_tracking == 'task_in_project' for service_tracking in order.order_line.mapped('product_id.service_tracking')
            )

    @api.depends('order_line.product_id', 'order_line.project_id')
    def _compute_project_ids(self):
        is_project_manager = self.env.user.has_group('project.group_project_manager')
        projects = self.env['project.project'].search([('sale_order_id', 'in', self.ids)])
        projects_per_so = defaultdict(lambda: self.env['project.project'])
        for project in projects:
            projects_per_so[project.sale_order_id.id] |= project
        for order in self:
            projects = order.order_line.mapped('product_id.project_id')
            projects |= order.order_line.mapped('project_id')
            projects |= projects_per_so[order.id or order._origin.id]
            if not is_project_manager:
                projects = projects._filtered_access('read')
            order.project_ids = projects
            order.project_count = len(projects)

    def _action_confirm(self):
        """ On SO confirmation, some lines should generate a task or a project. """
        if len(self.company_id) == 1:
            # All orders are in the same company
            self.order_line.sudo().with_company(self.company_id)._timesheet_service_generation()
        else:
            # Orders from different companies are confirmed together
            for order in self:
                order.order_line.sudo().with_company(order.company_id)._timesheet_service_generation()
        return super()._action_confirm()

    def action_view_task(self):
        self.ensure_one()
        if not self.order_line:
            return {'type': 'ir.actions.act_window_close'}

        list_view_id = self.env.ref('project.view_task_tree2').id
        form_view_id = self.env.ref('project.view_task_form2').id
        kanban_view_id = self.env.ref('project.view_task_kanban_inherit_view_default_project').id

        project_ids = self.tasks_ids.project_id
        if len(project_ids) > 1:
            action = self.env['ir.actions.actions']._for_xml_id('project.action_view_task')
            action['domain'] = AND([ast.literal_eval(action['domain']), [('id', 'in', self.tasks_ids.ids)]])
            action['context'] = {}
        else:
            # Load top bar if all the tasks linked to the SO belong to the same project
            action = self.env['ir.actions.actions'].with_context({'active_id': project_ids.id})._for_xml_id('project.act_project_project_2_project_task_all')
            action['context'] = {
                'active_id': project_ids.id,
                'search_default_sale_order_id': self.id,
            }

        if self.tasks_count > 1:  # cross project kanban task
            for idx, (view_id, view_type) in enumerate(action['views']):
                if view_type == 'kanban':
                    action['views'][idx] = (kanban_view_id, 'kanban')
                elif view_type == 'list':
                    action['views'][idx] = (list_view_id, 'list')
                elif view_type == 'form':
                    action['views'][idx] = (form_view_id, 'form')
        else:  # 1 or 0 tasks -> form view
            action['views'] = [(form_view_id, 'form')]
            action['res_id'] = self.tasks_ids.id
        # set default project
        default_line = next((sol for sol in self.order_line if sol.product_id.type == 'service'), self.env['sale.order.line'])
        default_project_id = default_line.project_id.id or self.project_ids[:1].id or self.tasks_ids.project_id[:1].id

        action['context'].update({
            'default_sale_order_id': self.id,
            'default_sale_line_id': default_line.id,
            'default_partner_id': self.partner_id.id,
            'default_project_id': default_project_id,
            'default_user_ids': [self.env.uid],
        })
        return action

    def action_create_project(self):
        self.ensure_one()
        if not self.show_create_project_button:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("The project couldn't be created as the Sales Order must be confirmed, is already linked to a project, or doesn't involve any services."),
                }
            }

        sorted_line = self.order_line.sorted('sequence')
        default_sale_line = next((
            sol for sol in sorted_line
            if sol.product_id.type == 'service' and not sol.is_downpayment
        ), self.env['sale.order.line'])
        return {
            **self.env["ir.actions.actions"]._for_xml_id("project.open_create_project"),
            'context': {
                'default_sale_order_id': self.id,
                'default_sale_line_id': default_sale_line.id,
                'default_partner_id': self.partner_id.id,
                'default_user_ids': [self.env.uid],
                'default_allow_billable': 1,
                'hide_allow_billable': True,
                'default_company_id': self.company_id.id,
                'generate_milestone': default_sale_line.product_id.service_policy == 'delivered_milestones',
            },
        }

    def action_view_project_ids(self):
        self.ensure_one()
        if not self.order_line:
            return {'type': 'ir.actions.act_window_close'}

        sorted_line = self.order_line.sorted('sequence')
        default_sale_line = next((
            sol for sol in sorted_line if sol.product_id.type == 'service'
        ), self.env['sale.order.line'])
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Projects'),
            'domain': ['|', ('sale_order_id', '=', self.id), ('id', 'in', self.with_context(active_test=False).project_ids.ids), ('active', 'in', [True, False])],
            'res_model': 'project.project',
            'views': [(False, 'kanban'), (False, 'list'), (False, 'form')],
            'view_mode': 'kanban,list,form',
            'context': {
                **self._context,
                'default_partner_id': self.partner_id.id,
                'default_sale_line_id': default_sale_line.id,
                'default_allow_billable': 1,
            }
        }
        if len(self.with_context(active_test=False).project_ids) == 1:
            action.update({'views': [(False, 'form')], 'res_id': self.project_ids.id})
        return action

    def action_view_milestone(self):
        self.ensure_one()
        default_project = self.project_ids and self.project_ids[0]
        sorted_line = self.order_line.sorted('sequence')
        default_sale_line = next((
            sol for sol in sorted_line
                if sol.is_service and sol.product_id.service_policy == 'delivered_milestones'
        ), self.env['sale.order.line'])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Milestones'),
            'domain': [('sale_line_id', 'in', self.order_line.ids)],
            'res_model': 'project.milestone',
            'views': [(self.env.ref('sale_project.sale_project_milestone_view_tree').id, 'list')],
            'view_mode': 'list',
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    No milestones found. Let's create one!
                </p><p>
                    Track major progress points that must be reached to achieve success.
                </p>
            """),
            'context': {
                **self.env.context,
                'default_project_id': default_project.id,
                'default_sale_line_id': default_sale_line.id,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        created_records = super().create(vals_list)
        project = self.env['project.project'].browse(self.env.context.get('create_for_project_id'))
        if project:
            service_sol = next((sol for sol in created_records.order_line if sol.is_service), False)
            if not service_sol and not self.env.context.get('from_embedded_action'):
                raise UserError(_('This Sales Order must contain at least one product of type "Service".'))
            if not project.sale_line_id:
                project.sale_line_id = service_sol
        return created_records

    def write(self, values):
        res = super().write(values)
        if 'state' in values and values['state'] == 'cancel':
            # Remove sale line field reference from all projects
            self.env['project.project'].sudo().search([('sale_line_id.order_id', 'in', self.ids)]).sale_line_id = False
        return res

    def _prepare_analytic_account_data(self, prefix=None):
        """ Prepare SO analytic account creation values.

        :return: `account.analytic.account` creation values
        :rtype: dict
        """
        self.ensure_one()
        name = self.name
        if prefix:
            name = prefix + ": " + self.name
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        return {
            'name': name,
            'code': self.client_order_ref,
            'company_id': self.company_id.id,
            'plan_id': project_plan.id,
            'partner_id': self.partner_id.id,
        }

    def _compute_completed_task_percentage(self):
        for so in self:
            so.completed_task_percentage = so.tasks_count and so.closed_task_count / so.tasks_count
