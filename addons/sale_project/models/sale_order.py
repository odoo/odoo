# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _, Command
from odoo.tools.misc import clean_context
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tasks_ids = fields.Many2many('project.task', compute='_compute_tasks_ids', search='_search_tasks_ids', string='Tasks associated to this sale')
    tasks_count = fields.Integer(string='Tasks', compute='_compute_tasks_ids', groups="project.group_project_user")

    visible_project = fields.Boolean('Display project', compute='_compute_visible_project', readonly=True)
    project_id = fields.Many2one(
        'project.project', 'Project', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help='Select a non billable project on which tasks can be created.')
    project_ids = fields.Many2many('project.project', compute="_compute_project_ids", string='Projects', copy=False, groups="project.group_project_user", help="Projects used in this sales order.")
    project_count = fields.Integer(string='Number of Projects', compute='_compute_project_ids', groups='project.group_project_user')
    milestone_count = fields.Integer(compute='_compute_milestone_count')
    is_product_milestone = fields.Boolean(compute='_compute_is_product_milestone')

    def _compute_milestone_count(self):
        read_group = self.env['project.milestone']._read_group(
            [('sale_line_id', 'in', self.order_line.ids)],
            ['sale_line_id'],
            ['sale_line_id'],
        )
        line_data = {res['sale_line_id'][0]: res['sale_line_id_count'] for res in read_group}
        for order in self:
            order.milestone_count = sum(line_data.get(line.id, 0) for line in order.order_line)

    def _compute_is_product_milestone(self):
        for order in self:
            order.is_product_milestone = order.order_line.product_id.filtered(lambda p: p.service_policy == 'delivered_milestones')

    def _search_tasks_ids(self, operator, value):
        is_name_search = operator in ['=', '!=', 'like', '=like', 'ilike', '=ilike'] and isinstance(value, str)
        is_id_eq_search = operator in ['=', '!='] and isinstance(value, int)
        is_id_in_search = operator in ['in', 'not in'] and isinstance(value, list) and all(isinstance(item, int) for item in value)
        if not (is_name_search or is_id_eq_search or is_id_in_search):
            raise NotImplementedError(_('Operation not supported'))

        if is_name_search:
            tasks_ids = self.env['project.task']._name_search(value, operator=operator, limit=None)
        elif is_id_eq_search:
            tasks_ids = value if operator == '=' else self.env['project.task']._search([('id', '!=', value)], order='id')
        else:  # is_id_in_search
            tasks_ids = self.env['project.task']._search([('id', operator, value)], order='id')

        tasks = self.env['project.task'].browse(tasks_ids)
        return [('id', 'in', tasks.sale_order_id.ids)]

    @api.depends('order_line.product_id.project_id')
    def _compute_tasks_ids(self):
        tasks_per_so = self.env['project.task']._read_group(
            domain=self._tasks_ids_domain(),
            fields=['sale_order_id', 'ids:array_agg(id)'],
            groupby=['sale_order_id'],
        )
        so_to_tasks_and_count = {}
        for group in tasks_per_so:
            if group['sale_order_id']:
                so_to_tasks_and_count[group['sale_order_id'][0]] = {'task_ids': group['ids'], 'count': group['sale_order_id_count']}
            else:
                # tasks that have no sale_order_id need to be associated with the SO from their sale_line_id
                for task in self.env['project.task'].browse(group['ids']):
                    so_to_tasks_item = so_to_tasks_and_count.setdefault(task.sale_line_id.order_id.id, {'task_ids': [], 'count': 0})
                    so_to_tasks_item['task_ids'].append(task.id)
                    so_to_tasks_item['count'] += 1

        for order in self:
            order.tasks_ids = [Command.set(so_to_tasks_and_count.get(order.id, {}).get('task_ids', []))]
            order.tasks_count = so_to_tasks_and_count.get(order.id, {}).get('count', 0)

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
        is_project_manager = self.user_has_groups('project.group_project_manager')
        projects = self.env['project.project'].search([('sale_order_id', 'in', self.ids)])
        projects_per_so = defaultdict(lambda: self.env['project.project'])
        for project in projects:
            projects_per_so[project.sale_order_id.id] |= project
        for order in self:
            projects = order.order_line.mapped('product_id.project_id')
            projects |= order.order_line.mapped('project_id')
            projects |= order.project_id
            projects |= projects_per_so[order.id or order._origin.id]
            if not is_project_manager:
                projects = projects._filter_access_rules('read')
            order.project_ids = projects
            order.project_count = len(projects)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Set the SO analytic account to the selected project's analytic account """
        if self.project_id.analytic_account_id:
            self.analytic_account_id = self.project_id.analytic_account_id

    def _action_confirm(self):
        """ On SO confirmation, some lines should generate a task or a project. """
        result = super()._action_confirm()
        context = clean_context(self._context)
        if len(self.company_id) == 1:
            # All orders are in the same company
            self.order_line.sudo().with_context(context).with_company(self.company_id)._timesheet_service_generation()
        else:
            # Orders from different companies are confirmed together
            for order in self:
                order.order_line.sudo().with_context(context).with_company(order.company_id)._timesheet_service_generation()
        return result

    def action_view_task(self):
        self.ensure_one()

        list_view_id = self.env.ref('project.view_task_tree2').id
        form_view_id = self.env.ref('project.view_task_form2').id

        action = {'type': 'ir.actions.act_window_close'}
        task_projects = self.tasks_ids.mapped('project_id')
        if len(task_projects) == 1 and len(self.tasks_ids) > 1:  # redirect to task of the project (with kanban stage, ...)
            action = self.with_context(active_id=task_projects.id).env['ir.actions.actions']._for_xml_id(
                'project.act_project_project_2_project_task_all')
            if action.get('context'):
                eval_context = self.env['ir.actions.actions']._get_eval_context()
                eval_context.update({'active_id': task_projects.id})
                action_context = safe_eval(action['context'], eval_context)
                action_context.update(eval_context)
                action['context'] = action_context
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("project.action_view_task")
            action['context'] = {}  # erase default context to avoid default filter
            if len(self.tasks_ids) > 1:  # cross project kanban task
                action['views'] = [[False, 'kanban'], [list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'calendar'], [False, 'pivot']]
            elif len(self.tasks_ids) == 1:  # single task -> form view
                action['views'] = [(form_view_id, 'form')]
                action['res_id'] = self.tasks_ids.id
        # filter on the task of the current SO
        action['domain'] = self._tasks_ids_domain()
        action.setdefault('context', {})
        return action

    def _tasks_ids_domain(self):
        return ['&', ('display_project_id', '!=', False), '|', ('sale_line_id', 'in', self.order_line.ids), ('sale_order_id', 'in', self.ids)]

    def action_view_project_ids(self):
        self.ensure_one()
        view_form_id = self.env.ref('project.edit_project').id
        view_kanban_id = self.env.ref('project.view_project_kanban').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.with_context(active_test=False).project_ids.ids), ('active', 'in', [True, False])],
            'view_mode': 'kanban,form',
            'name': _('Projects'),
            'res_model': 'project.project',
        }
        if len(self.with_context(active_test=False).project_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.project_ids.id})
        else:
            action['views'] = [(view_kanban_id, 'kanban'), (view_form_id, 'form')]
        return action

    def action_view_milestone(self):
        self.ensure_one()
        default_project = self.project_ids and self.project_ids[0]
        default_sale_line = default_project.sale_line_id or self.order_line and self.order_line[0]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Milestones'),
            'domain': [('sale_line_id', 'in', self.order_line.ids)],
            'res_model': 'project.milestone',
            'views': [(self.env.ref('sale_project.sale_project_milestone_view_tree').id, 'tree')],
            'view_mode': 'tree',
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    No milestones found. Let's create one!
                </p><p>
                    Track major progress points that must be reached to achieve success.
                </p>
            """),
            'context': {
                **self.env.context,
                'default_project_id' : default_project.id,
                'default_sale_line_id' : default_sale_line.id,
            }
        }

    def write(self, values):
        if 'state' in values and values['state'] == 'cancel':
            self.project_id.sudo().sale_line_id = False
        return super(SaleOrder, self).write(values)

    def _prepare_analytic_account_data(self, prefix=None):
        result = super(SaleOrder, self)._prepare_analytic_account_data(prefix=prefix)
        result['plan_id'] = self.company_id.analytic_plan_id.id or result['plan_id']
        return result
