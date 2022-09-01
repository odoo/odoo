# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, Command, fields, models, _
from odoo.tools import format_amount
from odoo.tools.sql import column_exists, create_column


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_delivered_method = fields.Selection(selection_add=[('milestones', 'Milestones')])
    project_id = fields.Many2one(
        'project.project', 'Generated Project',
        index=True, copy=False)
    task_id = fields.Many2one(
        'project.task', 'Generated Task',
        index=True, copy=False)
    # used to know if generate a task and/or a project, depending on the product settings
    is_service = fields.Boolean("Is a Service", compute='_compute_is_service', store=True, compute_sudo=True)
    reached_milestones_ids = fields.One2many('project.milestone', 'sale_line_id', string='Reached Milestones', domain=[('is_reached', '=', True)])

    def name_get(self):
        res = super().name_get()
        with_price_unit = self.env.context.get('with_price_unit')
        if with_price_unit:
            names = dict(res)
            result = []
            sols_by_so_dict = defaultdict(lambda: self.env[self._name])  # key: (sale_order_id, product_id), value: sale order line
            for line in self:
                sols_by_so_dict[line.order_id.id, line.product_id.id] += line

            for sols in sols_by_so_dict.values():
                if len(sols) > 1 and all(sols.mapped('is_service')):
                    result += [(
                        line.id,
                        '%s - %s' % (
                            names.get(line.id), format_amount(self.env, line.price_unit, line.currency_id))
                    ) for line in sols]
                else:
                    result += [(line.id, names.get(line.id)) for line in sols]
            return result
        return res

    @api.depends('product_id.type')
    def _compute_is_service(self):
        for so_line in self:
            so_line.is_service = so_line.product_id.type == 'service'

    @api.depends('product_id.type')
    def _compute_product_updatable(self):
        super()._compute_product_updatable()
        for line in self:
            if line.product_id.type == 'service' and line.state == 'sale':
                line.product_updatable = False

    def _auto_init(self):
        """
        Create column to stop ORM from computing it himself (too slow)
        """
        if not column_exists(self.env.cr, 'sale_order_line', 'is_service'):
            create_column(self.env.cr, 'sale_order_line', 'is_service', 'bool')
            self.env.cr.execute("""
                UPDATE sale_order_line line
                SET is_service = (pt.type = 'service')
                FROM product_product pp
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pp.id = line.product_id
            """)
        return super()._auto_init()

    @api.depends('product_id')
    def _compute_qty_delivered_method(self):
        milestones_lines = self.filtered(lambda sol:
            not sol.is_expense
            and sol.product_id.type == 'service'
            and sol.product_id.service_type == 'milestones'
        )
        milestones_lines.qty_delivered_method = 'milestones'
        super(SaleOrderLine, self - milestones_lines)._compute_qty_delivered_method()

    @api.depends('qty_delivered_method', 'product_uom_qty', 'reached_milestones_ids.quantity_percentage')
    def _compute_qty_delivered(self):
        lines_by_milestones = self.filtered(lambda sol: sol.qty_delivered_method == 'milestones')
        super(SaleOrderLine, self - lines_by_milestones)._compute_qty_delivered()

        if not lines_by_milestones:
            return

        project_milestone_read_group = self.env['project.milestone'].read_group(
            [('sale_line_id', 'in', lines_by_milestones.ids), ('is_reached', '=', True)],
            ['sale_line_id', 'quantity_percentage'],
            ['sale_line_id'],
        )
        reached_milestones_per_sol = {res['sale_line_id'][0]: res['quantity_percentage'] for res in project_milestone_read_group}
        for line in lines_by_milestones:
            sol_id = line.id or line._origin.id
            line.qty_delivered = reached_milestones_per_sol.get(sol_id, 0.0) * line.product_uom_qty

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Do not generate task/project when expense SO line, but allow
        # generate task with hours=0.
        for line in lines:
            if line.state == 'sale' and not line.is_expense:
                line.sudo()._timesheet_service_generation()
                # if the SO line created a task, post a message on the order
                if line.task_id:
                    msg_body = _("Task Created (%s): %s", line.product_id.name, line.task_id._get_html_link())
                    line.order_id.message_post(body=msg_body)
        return lines

    def write(self, values):
        result = super().write(values)
        # changing the ordered quantity should change the planned hours on the
        # task, whatever the SO state. It will be blocked by the super in case
        # of a locked sale order.
        if 'product_uom_qty' in values and not self.env.context.get('no_update_planned_hours', False):
            for line in self:
                if line.task_id and line.product_id.type == 'service':
                    planned_hours = line._convert_qty_company_hours(line.task_id.company_id)
                    line.task_id.write({'planned_hours': planned_hours})
        return result

    ###########################################
    # Service : Project and task generation
    ###########################################

    def _convert_qty_company_hours(self, dest_company):
        return self.product_uom_qty

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        account = self.order_id.analytic_account_id
        if not account:
            service_products = self.order_id.order_line.product_id.filtered(lambda p: p.type == 'service' and p.default_code)
            default_code = service_products.default_code if len(service_products) == 1 else None
            self.order_id._create_analytic_account(prefix=default_code)
            account = self.order_id.analytic_account_id

        # create the project or duplicate one
        return {
            'name': '%s - %s' % (self.order_id.client_order_ref, self.order_id.name) if self.order_id.client_order_ref else self.order_id.name,
            'analytic_account_id': account.id,
            'analytic_tag_ids': [Command.set(self.analytic_tag_ids.ids)],
            'partner_id': self.order_id.partner_id.id,
            'sale_line_id': self.id,
            'active': True,
            'company_id': self.company_id.id,
        }

    def _timesheet_create_project(self):
        """ Generate project for the given so line, and link it.
            :param project: record of project.project in which the task should be created
            :return task: record of the created task
        """
        self.ensure_one()
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
            project.tasks.filtered('parent_id').write({
                'sale_line_id': self.id,
                'sale_order_id': self.order_id.id,
            })
        else:
            project_only_sol_count = self.env['sale.order.line'].search_count([
                ('order_id', '=', self.order_id.id),
                ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']),
            ])
            if project_only_sol_count == 1:
                values['name'] = "%s - [%s] %s" % (values['name'], self.product_id.default_code, self.product_id.name) if self.product_id.default_code else "%s - %s" % (values['name'], self.product_id.name)
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
            'name': title if project.sale_line_id else '%s - %s' % (self.order_id.name or '', title),
            'analytic_account_id': project.analytic_account_id.id,
            'analytic_tag_ids': [Command.set(project.analytic_tag_ids.ids)],
            'planned_hours': planned_hours,
            'partner_id': self.order_id.partner_id.id,
            'email_from': self.order_id.partner_id.email,
            'description': description,
            'project_id': project.id,
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
            'company_id': project.company_id.id,
            'user_ids': False,  # force non assigned task, as created as sudo()
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
        task_msg = _("This task has been created from: %s (%s)", self.order_id._get_html_link(), self.product_id.name)
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
            map_sol_project = {sol.id: sol.product_id.with_company(sol.company_id).project_id for sol in so_line_task_global_project}

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
                if map_sol_project.get(so_line.id) and so_line.product_uom_qty > 0:
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
            so_line._generate_milestone()

    def _generate_milestone(self):
        if self.product_id.service_policy == 'delivered_milestones':
            milestone = self.env['project.milestone'].create({
                'name': self.name,
                'project_id': self.project_id.id,
                'sale_line_id': self.id,
                'quantity_percentage': 1,
            })
            if self.product_id.service_tracking == 'task_in_project':
                self.task_id.milestone_id = milestone.id

    def _prepare_invoice_line(self, **optional_values):
        """
            If the sale order line isn't linked to a sale order which already have a default analytic account,
            this method allows to retrieve the analytic account which is linked to project or task directly linked
            to this sale order line, or the analytic account of the project which uses this sale order line, if it exists.
        """
        values = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if not values.get('analytic_account_id'):
            task_analytic_account = self.task_id._get_task_analytic_account_id() if self.task_id else False
            if task_analytic_account:
                values['analytic_account_id'] = task_analytic_account.id
            elif self.project_id.analytic_account_id:
                values['analytic_account_id'] = self.project_id.analytic_account_id.id
            elif self.is_service and not self.is_expense:
                task_analytic_account_id = self.env['project.task'].read_group([
                    ('sale_line_id', '=', self.id),
                    ('analytic_account_id', '!=', False),
                ], ['analytic_account_id'], ['analytic_account_id'])
                project_analytic_account_id = self.env['project.project'].read_group([
                    ('analytic_account_id', '!=', False),
                    '|',
                        ('sale_line_id', '=', self.id),
                        '&',
                            ('tasks.sale_line_id', '=', self.id),
                            ('tasks.analytic_account_id', '=', False)
                ], ['analytic_account_id'], ['analytic_account_id'])
                analytic_account_ids = {rec['analytic_account_id'][0] for rec in (task_analytic_account_id + project_analytic_account_id)}
                if len(analytic_account_ids) == 1:
                    values['analytic_account_id'] = analytic_account_ids.pop()
        if self.task_id.analytic_tag_ids:
            values['analytic_tag_ids'] += [Command.link(tag_id.id) for tag_id in self.task_id.analytic_tag_ids]
        if self.task_id.analytic_tag_ids or self.task_id.project_id.analytic_tag_ids:
            values['analytic_tag_ids'] += [Command.link(tag_id.id) for tag_id in self.task_id.analytic_tag_ids | self.task_id.project_id.analytic_tag_ids]
        elif self.is_service and not self.is_expense:
            tag_ids = self.env['account.analytic.tag'].search([
                '|', ('task_ids.sale_line_id', '=', self.id), ('project_ids.sale_line_id', '=', self.id)
            ])
            values['analytic_tag_ids'] += [Command.link(tag_id.id) for tag_id in tag_ids]
        return values

    def _get_action_per_item(self):
        """ Get action per Sales Order Item

            :returns: Dict containing id of SOL as key and the action as value
        """
        return {}
