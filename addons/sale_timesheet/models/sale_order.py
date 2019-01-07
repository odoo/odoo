# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', string='Timesheet activities associated to this sale')
    timesheet_count = fields.Float(string='Timesheet activities', compute='_compute_timesheet_ids', groups="hr_timesheet.group_hr_timesheet_user")

    tasks_ids = fields.Many2many('project.task', compute='_compute_tasks_ids', string='Tasks associated to this sale')
    tasks_count = fields.Integer(string='Tasks', compute='_compute_tasks_ids', groups="project.group_project_user")

    project_project_id = fields.Many2one('project.project', compute='_compute_project_project_id', string='Project associated to this sale')
    project_ids = fields.Many2many('project.project', compute="_compute_project_ids", string='Projects', copy=False, groups="project.group_project_user", help="Projects used in this sales order.")

    @api.multi
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

    @api.multi
    @api.depends('order_line.product_id.project_id')
    def _compute_tasks_ids(self):
        for order in self:
            order.tasks_ids = self.env['project.task'].search([('sale_line_id', 'in', order.order_line.ids)])
            order.tasks_count = len(order.tasks_ids)

    @api.multi
    @api.depends('analytic_account_id.project_ids')
    def _compute_project_project_id(self):
        for order in self:
            order.project_project_id = self.env['project.project'].search([('analytic_account_id', '=', order.analytic_account_id.id)])

    @api.multi
    @api.depends('order_line.product_id', 'project_project_id')
    def _compute_project_ids(self):
        for order in self:
            projects = order.order_line.mapped('product_id.project_id')
            if order.project_project_id:
                projects |= order.project_project_id
            order.project_ids = projects

    @api.multi
    def action_confirm(self):
        """ On SO confirmation, some lines should generate a task or a project. """
        result = super(SaleOrder, self).action_confirm()
        self.order_line._timesheet_service_generation()
        return result

    @api.multi
    def action_view_task(self):
        self.ensure_one()
        action = self.env.ref('project.action_view_task')
        list_view_id = self.env.ref('project.view_task_tree2').id
        form_view_id = self.env.ref('project.view_task_form2').id

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[False, 'kanban'], [list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'calendar'], [False, 'pivot'], [False, 'graph']],
            'target': action.target,
            'context': "{'group_by':'stage_id'}",
            'res_model': action.res_model,
        }
        if len(self.tasks_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % self.tasks_ids.ids
        elif len(self.tasks_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = self.tasks_ids.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.multi
    def action_view_project_ids(self):
        self.ensure_one()
        if len(self.project_ids) == 1:
            if self.env.user.has_group("hr_timesheet.group_hr_timesheet_user"):
                action = self.project_ids.action_view_timesheet_plan()
            else:
                action = self.env.ref("project.act_project_project_2_project_task_all").read()[0]
                action['context'] = safe_eval(action.get('context', '{}'), {'active_id': self.project_ids.id, 'active_ids': self.project_ids.ids})
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

    @api.multi
    def action_view_timesheet(self):
        self.ensure_one()
        action = self.env.ref('hr_timesheet.act_hr_timesheet_line')
        list_view_id = self.env.ref('hr_timesheet.hr_timesheet_line_tree').id
        form_view_id = self.env.ref('hr_timesheet.hr_timesheet_line_form').id

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if self.timesheet_count > 0:
            result['domain'] = "[('id','in',%s)]" % self.timesheet_ids.ids
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    task_id = fields.Many2one('project.task', 'Task', index=True, help="Task generated by the sales order item")
    is_service = fields.Boolean("Is a Service", compute='_compute_is_service', store=True, compute_sudo=True, help="Sales Order item should generate a task and/or a project, depending on the product settings.")

    @api.multi
    @api.depends('product_id.type')
    def _compute_is_service(self):
        for so_line in self:
            so_line.is_service = so_line.product_id.type == 'service'

    @api.depends('product_id.type')
    def _compute_product_updatable(self):
        for line in self:
            if line.product_id.type == 'service' and line.state == 'sale':
                line.product_updatable = False
            else:
                super(SaleOrderLine, line)._compute_product_updatable()

    @api.model
    def create(self, values):
        line = super(SaleOrderLine, self).create(values)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # check ordered quantity to avoid create project/task when expensing service products
        if line.state == 'sale' and not float_is_zero(line.product_uom_qty, precision_digits=precision):
            line._timesheet_service_generation()
        return line

    ###########################################
    ### Analytic : auto recompute delivered quantity
    ###########################################

    def _timesheet_compute_delivered_quantity_domain(self):
        # TODO JEM: avoid increment delivered for all AAL or just timesheet ?
        # see nim commit https://github.com/odoo/odoo/commit/21fbb9776a5fbd1838b189f1f7cf8c5d40663e14
        so_line_ids = self.filtered(lambda sol: sol.product_id.service_type != 'manual').ids
        return ['&', ('so_line', 'in', so_line_ids), ('project_id', '!=', False)]

    @api.multi
    def _analytic_compute_delivered_quantity_domain(self):
        domain = super(SaleOrderLine, self)._analytic_compute_delivered_quantity_domain()
        domain = expression.AND([domain, [('project_id', '=', False)]])
        timesheet_domain = self._timesheet_compute_delivered_quantity_domain()
        return expression.OR([domain, timesheet_domain])

    ###########################################
    ## Service : Project and task generation
    ###########################################

    def _convert_qty_company_hours(self):
        company_time_uom_id = self.env.user.company_id.project_time_mode_id
        if self.product_uom.id != company_time_uom_id.id and self.product_uom.category_id.id == company_time_uom_id.category_id.id:
            planned_hours = self.product_uom._compute_quantity(self.product_uom_qty, company_time_uom_id)
        else:
            planned_hours = self.product_uom_qty
        return planned_hours

    def _timesheet_find_project(self):
        self.ensure_one()
        Project = self.env['project.project']
        project = self.product_id.with_context(force_company=self.company_id.id).project_id
        if not project:
            # find the project corresponding to the analytic account of the sales order
            account = self.order_id.analytic_account_id
            if not account:
                self.order_id._create_analytic_account(prefix=self.product_id.default_code or None)
                account = self.order_id.analytic_account_id
            project = Project.search([('analytic_account_id', '=', account.id)], limit=1)
            if not project:
                project_name = '%s (%s)' % (account.name, self.order_partner_id.ref) if self.order_partner_id.ref else account.name
                project = Project.create({
                    'name': project_name,
                    'allow_timesheets': self.product_id.service_type == 'timesheet',
                    'analytic_account_id': account.id,
                })
                # set the SO line origin if product should create project
                if not project.sale_line_id and self.product_id.service_tracking in ['task_new_project', 'project_only']:
                    project.write({'sale_line_id': self.id})
        return project

    def _timesheet_create_task_prepare_values(self):
        self.ensure_one()
        project = self._timesheet_find_project()
        planned_hours = self._convert_qty_company_hours()
        return {
            'name': '%s:%s' % (self.order_id.name or '', self.name.split('\n')[0] or self.product_id.name),
            'planned_hours': planned_hours,
            'remaining_hours': planned_hours,
            'partner_id': self.order_id.partner_id.id,
            'description': self.name + '<br/>',
            'project_id': project.id,
            'sale_line_id': self.id,
            'company_id': self.company_id.id,
            'email_from': self.order_id.partner_id.email,
            'user_id': False, # force non assigned task, as created as sudo()
        }

    @api.multi
    def _timesheet_create_task(self):
        """ Generate task for the given so line, and link it.

            :return a mapping with the so line id and its linked task
            :rtype dict
        """
        result = {}
        for so_line in self:
            # create task
            values = so_line._timesheet_create_task_prepare_values()
            task = self.env['project.task'].sudo().create(values)
            so_line.write({'task_id': task.id})
            # post message on SO
            msg_body = _("Task Created (%s): <a href=# data-oe-model=project.task data-oe-id=%d>%s</a>") % (so_line.product_id.name, task.id, task.name)
            so_line.order_id.message_post(body=msg_body)
            # post message on task
            task_msg = _("This task has been created from: <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a> (%s)") % (so_line.order_id.id, so_line.order_id.name, so_line.product_id.name)
            task.message_post(body=task_msg)

            result[so_line.id] = task
        return result

    @api.multi
    def _timesheet_find_task(self):
        """ Find the task generated by the so lines. If no task linked, it will be
            created automatically.

            :return a mapping with the so line id and its linked task
            :rtype dict
        """
        # one search for all so lines
        tasks = self.env['project.task'].search([('sale_line_id', 'in', self.ids)])
        task_sol_mapping = {task.sale_line_id.id: task for task in tasks}

        result = {}
        for so_line in self:
            # If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a new task.
            task = task_sol_mapping.get(so_line.id)
            # If not found, create one task for the so line
            if not task:
                task = so_line._timesheet_create_task()[so_line.id]
            result[so_line.id] = task
        return result

    @api.multi
    def _timesheet_service_generation(self):
        """ For service lines, create the task or the project. If already exists, it simply links
            the existing one to the line.
        """
        for so_line in self.filtered(lambda sol: sol.is_service):
            # create task
            if so_line.product_id.service_tracking == 'task_global_project':
                so_line._timesheet_find_task()
            # create project
            if so_line.product_id.service_tracking == 'project_only':
                so_line._timesheet_find_project()
            # create project and task
            if so_line.product_id.service_tracking == 'task_new_project':
                so_line._timesheet_find_task()
