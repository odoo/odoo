# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, Command, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import format_list
from odoo.tools.sql import column_exists, create_column


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_delivered_method = fields.Selection(selection_add=[('milestones', 'Milestones')])
    project_id = fields.Many2one(
        'project.project', 'Generated Project',
        index=True, copy=False, export_string_translation=False)
    task_id = fields.Many2one(
        'project.task', 'Generated Task',
        index=True, copy=False, export_string_translation=False)
    reached_milestones_ids = fields.One2many('project.milestone', 'sale_line_id', string='Reached Milestones', domain=[('is_reached', '=', True)], export_string_translation=False)

    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('form_view_ref') == 'sale_project.sale_order_line_view_form_editable':
            default_values = dict()
            # If we can't add order lines to the default order, discard it
            if 'order_id' in res:
                try:
                    self.env['sale.order'].browse(res['order_id']).check_access('write')
                except AccessError:
                    del res['order_id']

            if 'order_id' in fields and not res.get('order_id'):
                assert (partner_id := self.env.context.get('default_partner_id'))
                project_id = self.env.context.get('link_to_project')
                sale_order = None
                so_create_values = {
                    'partner_id': partner_id,
                    'company_id': self.env.context.get('default_company_id') or self.env.company.id,
                }
                if project_id:
                    try:
                        project_so = self.env['project.project'].browse(project_id).sale_order_id
                        project_so.check_access('write')
                        sale_order = project_so
                    except AccessError:
                        pass
                    if not sale_order:
                        so_create_values['project_ids'] = [Command.link(project_id)]

                if not sale_order:
                    sale_order = self.env['sale.order'].create(so_create_values)
                default_values['order_id'] = sale_order.id
            if product_name := self.env.context.get('sol_product_name') or self.env.context.get('default_name'):
                product = self.env['product.product'].search([
                    ('name', 'ilike', product_name),
                    ('type', '=', 'service'),
                    ('company_id', 'in', [False, self.env.company.id]),
                ], limit=1)
                if product:
                    default_values['product_id'] = product.id
                    # We need to remove the name from the defaults so that the
                    # name of the SOL is based on the full name of the product
                    # and not overwritten by what was typed in the field.
                    if "name" in res:
                        del res["name"]
            else:
                default_values['name'] = _("New Sales Order Item")
            return {**res, **default_values}
        return res

    @api.model
    def name_create(self, name):
        # To get the right product when creating a SOL on the fly, we need to get
        # the name that was entered in the field from the `default_get` method.
        # The easiest way of doing that is to store it in the context.
        if self.env.context.get('form_view_ref') == 'sale_project.sale_order_line_view_form_editable' and not self.env.context.get('action_view_sols'):
            self = self.with_context(sol_product_name=name)
        return super().name_create(name)

    @api.model
    def _add_missing_default_values(self, values):
        # When creating a SOL through the quick create, the name_create will be
        # called with whatever was typed in the field. However, we don't want
        # that value to overwrite the computed SOL name if we find a product.
        defaults = super()._add_missing_default_values(values)
        if self.env.context.get('form_view_ref') == 'sale_project.sale_order_line_view_form_editable' and not self.env.context.get('action_view_sols'):
            if "name" in defaults and "product_id" in defaults:
                del defaults["name"]
        return defaults

    @api.depends('product_id.type')
    def _compute_product_updatable(self):
        super()._compute_product_updatable()
        for line in self:
            if line.product_id.type == 'service' and line.state == 'sale':
                line.product_updatable = False

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

        project_milestone_read_group = self.env['project.milestone']._read_group(
            [('sale_line_id', 'in', lines_by_milestones.ids), ('is_reached', '=', True)],
            ['sale_line_id'],
            ['quantity_percentage:sum'],
        )
        reached_milestones_per_sol = {sale_line.id: percentage_sum for sale_line, percentage_sum in project_milestone_read_group}
        for line in lines_by_milestones:
            sol_id = line.id or line._origin.id
            line.qty_delivered = reached_milestones_per_sol.get(sol_id, 0.0) * line.product_uom_qty

    @api.depends('order_id.partner_id', 'product_id', 'order_id.project_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if line.display_type or line.analytic_distribution or not line.product_id:
                continue
            project = line.product_id.project_id or line.order_id.project_id
            distribution = project._get_analytic_distribution()
            if distribution:
                line.analytic_distribution = distribution

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Do not generate task/project when expense SO line, but allow
        # generate task with hours=0.
        for line in lines:
            if line.state == 'sale' and not line.is_expense:
                has_task = bool(line.task_id)
                line.sudo()._timesheet_service_generation()
                # if the SO line created a task, post a message on the order
                if line.task_id and not has_task:
                    msg_body = _("Task Created (%(name)s): %(link)s", name=line.product_id.name, link=line.task_id._get_html_link())
                    line.order_id.message_post(body=msg_body)
                if line.product_id.expense_policy not in [False, 'no'] and line.order_id.project_id and not line.order_id.project_account_id:
                    line.order_id.project_id._create_analytic_account()

        # Set a service SOL on the project, if any is given
        if project_id := self.env.context.get('link_to_project'):
            assert (service_line := next((line for line in lines if line.is_service), False))
            project = self.env['project.project'].browse(project_id)
            if not project.sale_line_id:
                project.sale_line_id = service_line
        return lines

    def write(self, values):
        result = super().write(values)
        # changing the ordered quantity should change the allocated hours on the
        # task, whatever the SO state. It will be blocked by the super in case
        # of a locked sale order.
        if 'product_uom_qty' in values and not self.env.context.get('no_update_allocated_hours', False):
            for line in self:
                if line.task_id and line.product_id.type == 'service':
                    allocated_hours = line._convert_qty_company_hours(line.task_id.company_id or self.env.user.company_id)
                    line.task_id.write({'allocated_hours': allocated_hours})
        return result

    def copy_data(self, default=None):
        data = super().copy_data(default)
        for origin, datum in zip(self, data):
            if origin.analytic_distribution == origin.order_id.project_id.sudo()._get_analytic_distribution():
                datum['analytic_distribution'] = False
        return data

    ###########################################
    # Service : Project and task generation
    ###########################################

    def _convert_qty_company_hours(self, dest_company):
        return self.product_uom_qty

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        # create the project or duplicate one
        return {
            'name': '%s - %s' % (self.order_id.client_order_ref, self.order_id.name) if self.order_id.client_order_ref else self.order_id.name,
            'partner_id': self.order_id.partner_id.id,
            'sale_line_id': self.id,
            'active': True,
            'company_id': self.company_id.id,
            'allow_billable': True,
            'user_id': self.product_id.project_template_id.user_id.id,
        }

    def _timesheet_create_project(self):
        """ Generate project for the given so line, and link it.
            :param project: record of project.project in which the task should be created
            :return: record of the created project
        """
        self.ensure_one()
        values = self._timesheet_create_project_prepare_values()
        project_template = self.product_id.project_template_id
        if project_template:
            values['name'] = "%s - %s" % (values['name'], project_template.name)
            values.update(self._timesheet_create_project_account_vals(project_template))
            order_project = project_template.copy(values)
            order_project.tasks.write({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id,
            })
            # duplicating a project doesn't set the SO on sub-tasks
            order_project.tasks.filtered('parent_id').write({
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
            values.update(self._timesheet_create_project_account_vals(self.order_id.project_id))
            order_project = self.env['project.project'].create(values)

        # Avoid new tasks to go to 'Undefined Stage'
        if not order_project.type_ids:
            order_project.type_ids = self.env['project.task.type'].create([{
                'name': name,
                'fold': fold,
                'sequence': sequence,
            } for name, fold, sequence in [
                (_('To Do'), False, 5),
                (_('In Progress'), False, 10),
                (_('Done'), False, 15),
                (_('Cancelled'), True, 20),
            ]])

        # link project as generated by current so line
        self.write({'project_id': order_project.id})
        order_project.reinvoiced_sale_order_id = self.order_id
        return order_project

    def _timesheet_create_project_account_vals(self, project):
        return {
            **{fname: project[fname].id for fname in project._get_plan_fnames() if project[fname]},
            'account_id': self.env['account.analytic.account'].create(self.order_id._prepare_analytic_account_data()).id,
        }

    def _timesheet_create_task_prepare_values(self, project):
        self.ensure_one()
        allocated_hours = 0.0
        if self.product_id.service_type not in ['milestones', 'manual']:
            allocated_hours = self._convert_qty_company_hours(self.company_id)
        sale_line_name_parts = self.name.split('\n')
        title = sale_line_name_parts[0] or self.product_id.name
        description = '<br/>'.join(sale_line_name_parts[1:])
        return {
            'name': title if project.sale_line_id else '%s - %s' % (self.order_id.name or '', title),
            'allocated_hours': allocated_hours,
            'partner_id': self.order_id.partner_id.id,
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
        self.task_id = task
        # post message on task
        task_msg = _("This task has been created from: %(order_link)s (%(product_name)s)",
            order_link=self.order_id._get_html_link(),
            product_name=self.product_id.name,
        )
        task.message_post(body=task_msg)
        return task

    def _get_so_lines_task_global_project(self):
        return self.filtered(lambda sol: sol.is_service and sol.product_id.service_tracking == 'task_global_project')

    def _get_so_lines_new_project(self):
        return self.filtered(lambda sol: sol.is_service and sol.product_id.service_tracking in ['project_only', 'task_in_project'])

    def _timesheet_service_generation(self):
        """ For service lines, create the task or the project. If already exists, it simply links
            the existing one to the line.
            Note: If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a
            new project/task. This explains the searches on 'sale_line_id' on project/task. This also
            implied if so line of generated task has been modified, we may regenerate it.
        """
        so_line_task_global_project = self._get_so_lines_task_global_project()
        products_no_project = so_line_task_global_project.filtered(
            lambda sol: not (sol.product_id.project_id or sol.order_id.project_id)
        ).product_id
        if products_no_project:
            raise UserError(_(
                "A project must be defined on the quotation or on the form of products creating a task on order.\n"
                "The following products need a project in which to put their task: %(product_names)s",
                product_names=format_list(self.env, products_no_project.mapped('name')),
            ))
        so_line_new_project = self._get_so_lines_new_project()

        # search so lines from SO of current so lines having their project generated, in order to check if the current one can
        # create its own project, or reuse the one of its order.
        map_so_project = {}
        if so_line_new_project:
            order_ids = self.order_id.ids
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

        # task_global_project: create task in global project
        for so_line in so_line_task_global_project:
            if not so_line.task_id:
                project = map_sol_project.get(so_line.id) or so_line.order_id.project_id
                if project and so_line.product_uom_qty > 0:
                    so_line._timesheet_create_task(project)

        # project_only, task_in_project: create a new project, based or not on a template (1 per SO). May be create a task too.
        # if 'task_in_project' and project_id configured on SO, use that one instead
        for so_line in so_line_new_project:
            project = False
            if so_line.product_id.service_tracking in ['project_only', 'task_in_project']:
                project = so_line.project_id
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
            so_line._handle_milestones(project)

        # If the SO generates projects or create task in project on confirmation and the project of the SO is not set, set it to the project with the lowest sequence
        so_lines = so_line_task_global_project + so_line_new_project
        so = so_lines.order_id
        sol_projects = so_lines.project_id | so_lines.task_id.project_id
        if not so.project_id and sol_projects:
            so.project_id = sol_projects.sorted('sequence')[0]

    def _handle_milestones(self, project):
        self.ensure_one()
        if self.product_id.service_policy != 'delivered_milestones':
            return
        if (milestones := project.milestone_ids.filtered(lambda milestone: not milestone.sale_line_id)):
            milestones.write({
                'sale_line_id': self.id,
                'product_uom_qty': self.product_uom_qty / len(milestones),
            })
        else:
            milestone = self.env['project.milestone'].create({
                'name': self.name,
                'project_id': self.project_id.id or self.order_id.project_id.id,
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
        values = super()._prepare_invoice_line(**optional_values)
        if not values.get('analytic_distribution'):
            if self.task_id.project_id.account_id:
                values['analytic_distribution'] = {self.task_id.project_id.account_id.id: 100}
            elif self.project_id.account_id:
                values['analytic_distribution'] = {self.project_id.account_id.id: 100}
            elif self.is_service and not self.is_expense:
                [accounts] = self.env['project.project']._read_group([
                    ('account_id', '!=', False),
                    '|',
                        ('sale_line_id', '=', self.id),
                        ('tasks.sale_line_id', '=', self.id),
                ], aggregates=['account_id:recordset'])[0]
                if len(accounts) == 1:
                    values['analytic_distribution'] = {accounts.id: 100}
        return values

    def _get_action_per_item(self):
        """ Get action per Sales Order Item

            :returns: Dict containing id of SOL as key and the action as value
        """
        return {}

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.project_id:
            values['project_id'] = self.order_id.project_id.id
        return values
