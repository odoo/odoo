# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', string='Timesheet activities associated to this sale')
    timesheet_count = fields.Float(string='Timesheet activities', compute='_compute_timesheet_ids', groups="hr_timesheet.group_hr_timesheet_user")

    tasks_ids = fields.Many2many('project.task', compute='_compute_tasks_ids', string='Tasks associated to this sale')
    tasks_count = fields.Integer(string='Tasks', compute='_compute_tasks_ids', groups="project.group_project_user")

    visible_project = fields.Boolean('Display project', compute='_compute_visible_project', readonly=True)
    project_id = fields.Many2one(
        'project.project', 'Project',
        domain="[('billable_type', 'in', ('no', 'task_rate')), ('analytic_account_id', '!=', False), ('company_id', '=', company_id)]",
        readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help='Select a non billable project on which tasks can be created.')
    project_ids = fields.Many2many('project.project', compute="_compute_project_ids", string='Projects', copy=False, groups="project.group_project_user", help="Projects used in this sales order.")
    timesheet_encode_uom_id = fields.Many2one('uom.uom', related='company_id.timesheet_encode_uom_id')
    timesheet_total_duration = fields.Float("Timesheet Total Duration", compute='_compute_timesheet_total_duration', help="Total recorded duration, expressed in the encoding UoM")

    @api.depends('analytic_account_id.line_ids')
    def _compute_timesheet_ids(self):
        for order in self:
            if order.analytic_account_id:
                order.timesheet_ids = self.env['account.analytic.line'].search(
                    [('so_line', 'in', order.order_line.ids),
                        ('amount', '<=', 0.0),
                        ('project_id', '!=', False)])
            else:
                order.timesheet_ids = []
            order.timesheet_count = len(order.timesheet_ids)

    @api.depends('order_line.product_id.project_id')
    def _compute_tasks_ids(self):
        for order in self:
            order.tasks_ids = self.env['project.task'].search(['|', ('sale_line_id', 'in', order.order_line.ids), ('sale_order_id', '=', order.id)])
            order.tasks_count = len(order.tasks_ids)

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
        for order in self:
            projects = order.order_line.mapped('product_id.project_id')
            projects |= order.order_line.mapped('project_id')
            projects |= order.project_id
            order.project_ids = projects

    @api.depends('timesheet_ids', 'company_id.timesheet_encode_uom_id')
    def _compute_timesheet_total_duration(self):
        for sale_order in self:
            duration_list = []
            for timesheet in sale_order.timesheet_ids:
                duration_list.append(timesheet.unit_amount)
            sale_order.timesheet_total_duration = sum(duration_list)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Set the SO analytic account to the selected project's analytic account """
        if self.project_id.analytic_account_id:
            self.analytic_account_id = self.project_id.analytic_account_id

    def _action_confirm(self):
        """ On SO confirmation, some lines should generate a task or a project. """
        result = super(SaleOrder, self)._action_confirm()
        for order in self:
            order.mapped('order_line').sudo().with_context(
                force_company=order.company_id.id,
            )._timesheet_service_generation()
        return result

    def action_view_task(self):
        self.ensure_one()

        list_view_id = self.env.ref('project.view_task_tree2').id
        form_view_id = self.env.ref('project.view_task_form2').id

        action = {'type': 'ir.actions.act_window_close'}

        task_projects = self.tasks_ids.mapped('project_id')
        if len(task_projects) == 1 and len(self.tasks_ids) > 1:  # redirect to task of the project (with kanban stage, ...)
            action = self.with_context(active_id=task_projects.id).env.ref(
                'project.act_project_project_2_project_task_all').read()[0]
            if action.get('context'):
                eval_context = self.env['ir.actions.actions']._get_eval_context()
                eval_context.update({'active_id': task_projects.id})
                action['context'] = safe_eval(action['context'], eval_context)
        else:
            action = self.env.ref('project.action_view_task').read()[0]
            action['context'] = {}  # erase default context to avoid default filter
            if len(self.tasks_ids) > 1:  # cross project kanban task
                action['views'] = [[False, 'kanban'], [list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'calendar'], [False, 'pivot']]
            elif len(self.tasks_ids) == 1:  # single task -> form view
                action['views'] = [(form_view_id, 'form')]
                action['res_id'] = self.tasks_ids.id
        # filter on the task of the current SO
        action.setdefault('context', {})
        action['context'].update({'search_default_sale_order_id': self.id})
        return action

    def action_view_project_ids(self):
        self.ensure_one()
        # redirect to form or kanban view
        billable_projects = self.project_ids.filtered(lambda project: project.sale_line_id)
        if len(billable_projects) == 1 and self.env.user.has_group('project.group_project_manager'):
            action = billable_projects[0].action_view_timesheet_plan()
        else:
            view_form_id = self.env.ref('project.edit_project').id
            view_kanban_id = self.env.ref('project.view_project_kanban').id
            action = {
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.project_ids.ids)],
                'views': [(view_kanban_id, 'kanban'), (view_form_id, 'form')],
                'view_mode': 'kanban,form',
                'name': _('Projects'),
                'res_model': 'project.project',
            }
        return action

    def action_view_timesheet(self):
        self.ensure_one()
        action = self.env.ref('sale_timesheet.timesheet_action_from_sales_order').read()[0]
        action['context'] = {}  # erase default filters
        if self.timesheet_count > 0:
            action['domain'] = [('so_line', 'in', self.order_line.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_delivered_method = fields.Selection(selection_add=[('timesheet', 'Timesheets')])
    project_id = fields.Many2one(
        'project.project', 'Generated Project',
        index=True, copy=False, help="Project generated by the sales order item")
    task_id = fields.Many2one(
        'project.task', 'Generated Task',
        index=True, copy=False, help="Task generated by the sales order item")
    is_service = fields.Boolean("Is a Service", compute='_compute_is_service', store=True, compute_sudo=True, help="Sales Order item should generate a task and/or a project, depending on the product settings.")
    analytic_line_ids = fields.One2many(domain=[('project_id', '=', False)])  # only analytic lines, not timesheets (since this field determine if SO line came from expense)

    @api.depends('product_id')
    def _compute_qty_delivered_method(self):
        """ Sale Timesheet module compute delivered qty for product [('type', 'in', ['service']), ('service_type', '=', 'timesheet')] """
        super(SaleOrderLine, self)._compute_qty_delivered_method()
        for line in self:
            if not line.is_expense and line.product_id.type == 'service' and line.product_id.service_type == 'timesheet':
                line.qty_delivered_method = 'timesheet'

    @api.depends('analytic_line_ids.project_id')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        lines_by_timesheet = self.filtered(lambda sol: sol.qty_delivered_method == 'timesheet')
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        mapping = lines_by_timesheet.sudo()._get_delivered_quantity_by_analytic(domain)
        for line in lines_by_timesheet:
            line.qty_delivered = mapping.get(line.id or line._origin.id, 0.0)

    def _timesheet_compute_delivered_quantity_domain(self):
        """ Hook for validated timesheet in addionnal module """
        return [('project_id', '!=', False)]

    @api.depends('product_id')
    def _compute_is_service(self):
        for so_line in self:
            so_line.is_service = so_line.product_id.type == 'service'

    @api.depends('product_id')
    def _compute_product_updatable(self):
        for line in self:
            if line.product_id.type == 'service' and line.state == 'sale':
                line.product_updatable = False
            else:
                super(SaleOrderLine, line)._compute_product_updatable()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        # Do not generate task/project when expense SO line, but allow
        # generate task with hours=0.
        for line in lines:
            if line.state == 'sale' and not line.is_expense:
                line.sudo()._timesheet_service_generation()
                # if the SO line created a task, post a message on the order
                if line.task_id:
                    msg_body = _("Task Created (%s): <a href=# data-oe-model=project.task data-oe-id=%d>%s</a>") % (line.product_id.name, line.task_id.id, line.task_id.name)
                    line.order_id.message_post(body=msg_body)
        return lines

    def write(self, values):
        result = super(SaleOrderLine, self).write(values)
        # changing the ordered quantity should change the planned hours on the
        # task, whatever the SO state. It will be blocked by the super in case
        # of a locked sale order.
        if 'product_uom_qty' in values:
            for line in self:
                if line.task_id:
                    planned_hours = line._convert_qty_company_hours(line.task_id.company_id)
                    line.task_id.write({'planned_hours': planned_hours})
        return result

    ###########################################
    # Service : Project and task generation
    ###########################################

    def _convert_qty_company_hours(self, dest_company):
        company_time_uom_id = dest_company.project_time_mode_id
        if self.product_uom.id != company_time_uom_id.id and self.product_uom.category_id.id == company_time_uom_id.category_id.id:
            planned_hours = self.product_uom._compute_quantity(self.product_uom_qty, company_time_uom_id)
        else:
            planned_hours = self.product_uom_qty
        return planned_hours

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        account = self.order_id.analytic_account_id
        if not account:
            self.order_id._create_analytic_account(prefix=self.product_id.default_code or None)
            account = self.order_id.analytic_account_id

        return {
            'name': '%s - %s' % (self.order_id.client_order_ref, self.order_id.name) if self.order_id.client_order_ref else self.order_id.name,
            'analytic_account_id': account.id,
            'partner_id': self.order_id.partner_id.id,
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
            'active': True,
            'company_id': self.company_id.id,
        }

    def _timesheet_create_project(self):
        """ Generate project for the given so line, and link it.
            :param project: record of project.project in which the task should be created
            :return task: record of the created task
        """
        self.ensure_one()
        # create the project or duplicate one
        values = self._timesheet_create_project_prepare_values()
        if self.product_id.project_template_id:
            values['name'] = "%s - %s" % (values['name'], self.product_id.project_template_id.name)
            project = self.product_id.project_template_id.copy(values)
            project.tasks.write({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id,
                'email_from': self.order_id.partner_id.email,
            })
            # duplicating a project doesn't set the SO on sub-tasks
            project.tasks.filtered(lambda task: task.parent_id != False).write({
                'sale_line_id': self.id,
            })
        else:
            project = self.env['project.project'].create(values)

        # Avoid new tasks to go to 'Undefined Stage'
        if not project.type_ids:
            project.type_ids = self.env['project.task.type'].create({'name': _('New')})

        # link project as generated by current so line
        self.write({'project_id': project.id})
        return project

    def _timesheet_create_task_prepare_values(self, project):
        self.ensure_one()
        planned_hours = self._convert_qty_company_hours(self.company_id)
        sale_line_name_parts = self.name.split('\n')
        title = sale_line_name_parts[0] or self.product_id.name
        description = '<br/>'.join(sale_line_name_parts[1:])
        return {
            'name': title if project.sale_line_id else '%s: %s' % (self.order_id.name or '', title),
            'planned_hours': planned_hours,
            'partner_id': self.order_id.partner_id.id,
            'email_from': self.order_id.partner_id.email,
            'description': description,
            'project_id': project.id,
            'sale_line_id': self.id,
            'company_id': project.company_id.id,
            'user_id': False,  # force non assigned task, as created as sudo()
        }

    def _timesheet_create_task(self, project):
        """ Generate task for the given so line, and link it.
            :param project: record of project.project in which the task should be created
            :return task: record of the created task
        """
        values = self._timesheet_create_task_prepare_values(project)
        task = self.env['project.task'].sudo().create(values)
        self.write({'task_id': task.id})
        # post message on task
        task_msg = _("This task has been created from: <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a> (%s)") % (self.order_id.id, self.order_id.name, self.product_id.name)
        task.message_post(body=task_msg)
        return task

    def _timesheet_service_generation(self):
        """ For service lines, create the task or the project. If already exists, it simply links
            the existing one to the line.
            Note: If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a
            new project/task. This explains the searches on 'sale_line_id' on project/task. This also
            implied if so line of generated task has been modified, we may regenerate it.
        """
        so_line_task_global_project = self.filtered(lambda sol: sol.is_service and sol.product_id.service_tracking == 'task_global_project')
        so_line_new_project = self.filtered(lambda sol: sol.is_service and sol.product_id.service_tracking in ['project_only', 'task_in_project'])

        # search so lines from SO of current so lines having their project generated, in order to check if the current one can
        # create its own project, or reuse the one of its order.
        map_so_project = {}
        if so_line_new_project:
            order_ids = self.mapped('order_id').ids
            so_lines_with_project = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '=', False)])
            map_so_project = {sol.order_id.id: sol.project_id for sol in so_lines_with_project}
            so_lines_with_project_templates = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '!=', False)])
            map_so_project_templates = {(sol.order_id.id, sol.product_id.project_template_id.id): sol.project_id for sol in so_lines_with_project_templates}

        # search the global project of current SO lines, in which create their task
        map_sol_project = {}
        if so_line_task_global_project:
            map_sol_project = {sol.id: sol.product_id.with_context(force_company=sol.company_id.id).project_id for sol in so_line_task_global_project}

        def _can_create_project(sol):
            if not sol.project_id:
                if sol.product_id.project_template_id:
                    return (sol.order_id.id, sol.product_id.project_template_id.id) not in map_so_project_templates
                elif sol.order_id.id not in map_so_project:
                    return True
            return False

        def _determine_project(so_line):
            """Determine the project for this sale order line.
            Rules are different based on the service_tracking:

            - 'project_only': the project_id can only come from the sale order line itself
            - 'task_in_project': the project_id comes from the sale order line only if no project_id was configured
              on the parent sale order"""

            if so_line.product_id.service_tracking == 'project_only':
                return so_line.project_id
            elif so_line.product_id.service_tracking == 'task_in_project':
                return so_line.order_id.project_id or so_line.project_id

            return False

        # task_global_project: create task in global project
        for so_line in so_line_task_global_project:
            if not so_line.task_id:
                if map_sol_project.get(so_line.id):
                    so_line._timesheet_create_task(project=map_sol_project[so_line.id])

        # project_only, task_in_project: create a new project, based or not on a template (1 per SO). May be create a task too.
        # if 'task_in_project' and project_id configured on SO, use that one instead
        for so_line in so_line_new_project:
            project = _determine_project(so_line)
            if not project and _can_create_project(so_line):
                project = so_line._timesheet_create_project()
                if so_line.product_id.project_template_id:
                    map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)] = project
                else:
                    map_so_project[so_line.order_id.id] = project
            elif not project:
                # Attach subsequent SO lines to the created project
                so_line.project_id = (
                    map_so_project_templates.get((so_line.order_id.id, so_line.product_id.project_template_id.id))
                    or map_so_project.get(so_line.order_id.id)
                )
            if so_line.product_id.service_tracking == 'task_in_project':
                if not project:
                    if so_line.product_id.project_template_id:
                        project = map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)]
                    else:
                        project = map_so_project[so_line.order_id.id]
                if not so_line.task_id:
                    so_line._timesheet_create_task(project=project)
