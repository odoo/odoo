# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.exceptions import AccessError, UserError


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

    def _get_product_from_sol_name_domain(self, product_name):
        return [
            ('name', 'ilike', product_name),
            ('type', '=', 'service'),
            ('company_id', 'in', [False, self.env.company.id]),
        ]

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('form_view_ref') == 'sale_project.sale_order_line_view_form_editable':
            default_values = {
                'name': _("New Sales Order Item"),
            }
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
                        sale_order = project_so or self.env['sale.order'].search([('project_id', '=', project_id)], limit=1)
                    except AccessError:
                        pass
                    if not sale_order:
                        so_create_values['project_ids'] = [Command.link(project_id)]

                if not sale_order:
                    sale_order = self.env['sale.order'].create(so_create_values)
                default_values['order_id'] = sale_order.id
            return {**res, **default_values}
        return res

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

    @api.depends('product_uom_qty', 'reached_milestones_ids.quantity_percentage')
    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()

    def _prepare_qty_delivered(self):
        lines_by_milestones = self.filtered(lambda sol: sol.qty_delivered_method == 'milestones')
        delivered_qties = super(SaleOrderLine, self - lines_by_milestones)._prepare_qty_delivered()

        if not lines_by_milestones:
            return delivered_qties

        project_milestone_read_group = self.env['project.milestone']._read_group(
            [('sale_line_id', 'in', lines_by_milestones.ids), ('is_reached', '=', True)],
            ['sale_line_id'],
            ['quantity_percentage:sum'],
        )
        reached_milestones_per_sol = {sale_line.id: percentage_sum for sale_line, percentage_sum in project_milestone_read_group}
        for line in lines_by_milestones:
            sol_id = line.id or line._origin.id
            delivered_qties[line] = reached_milestones_per_sol.get(sol_id, 0.0) * line.product_uom_qty
        return delivered_qties

    @api.depends('order_id.partner_id', 'product_id', 'order_id.project_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            project = line.product_id.project_id or line.order_id.project_id
            if line.display_type or not line.product_id or not project:
                continue

            if line.analytic_distribution:
                applied_root_plans = self.env['account.analytic.account'].browse(
                    list({int(account_id) for ids in line.analytic_distribution for account_id in ids.split(",")})
                ).exists().root_plan_id
                if accounts_to_add := project._get_analytic_accounts().filtered(
                    lambda account: account.root_plan_id not in applied_root_plans
                ):
                    # project account is added to each analytic distribution line
                    line.analytic_distribution = {
                        f"{account_ids},{','.join(map(str, accounts_to_add.ids))}": percentage
                        for account_ids, percentage in line.analytic_distribution.items()
                    }
            else:
                line.analytic_distribution = project._get_analytic_distribution()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Do not generate task/project when expense SO line, but allow
        # generate task with hours=0.
        confirmed_lines = lines.filtered(lambda sol: sol.state == 'sale' and not sol.is_expense)
        # We track the lines that already generated a task, so we know we won't have to post a message for them after calling the generation service
        has_task_lines = confirmed_lines.filtered('task_id')
        confirmed_lines.sudo()._timesheet_service_generation()
        # if the SO line created a task, post a message on the order
        for line in confirmed_lines - has_task_lines:
            if line.task_id:
                msg_body = _("Task Created (%(name)s): %(link)s", name=line.product_id.name, link=line.task_id._get_html_link())
                line.order_id.message_post(body=msg_body)

        # Set a service SOL on the project, if any is given
        if project_id := self.env.context.get('link_to_project'):
            assert (service_line := next((line for line in lines if line.is_service), False))
            project = self.env['project.project'].browse(project_id)
            if not project.sale_line_id:
                project.sale_line_id = service_line
                if not project.reinvoiced_sale_order_id:
                    project.reinvoiced_sale_order_id = service_line.order_id
        return lines

    def write(self, vals):
        sols_with_no_qty_ordered = self.env['sale.order.line']
        if 'product_uom_qty' in vals and vals.get('product_uom_qty') > 0:
            sols_with_no_qty_ordered = self.filtered(lambda sol: sol.product_uom_qty == 0)
        result = super().write(vals)
        # changing the ordered quantity should change the allocated hours on the
        # task, whatever the SO state. It will be blocked by the super in case
        # of a locked sale order.
        if vals.get('product_uom_qty') and sols_with_no_qty_ordered:
            sols_with_no_qty_ordered.filtered(lambda l: l.is_service and l.state == 'sale' and not l.is_expense)._timesheet_service_generation()
        if 'product_uom_qty' in vals and not self.env.context.get('no_update_allocated_hours', False):
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
            'account_id': self.env.context.get('project_account_id') or self.order_id.project_account_id.id or self.env['account.analytic.account'].create(self.order_id._prepare_analytic_account_data()).id,
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
            if project_template.is_template:
                project = project_template.action_create_from_template(values)
            else:
                project = project_template.copy(values)
            project.tasks.write({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id,
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
            values.update(self._timesheet_create_project_account_vals(self.order_id.project_id))
            project = self.env['project.project'].create(values)

        # Avoid new tasks to go to 'Undefined Stage'
        if not project.type_ids:
            project.type_ids = self.env['project.task.type'].create([{
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
        self.write({'project_id': project.id})
        project.reinvoiced_sale_order_id = self.order_id
        return project

    def _timesheet_create_project_account_vals(self, project):
        return {
            fname: project[fname].id for fname in project._get_plan_fnames() if fname != 'account_id' and project[fname]
        }

    def _timesheet_create_task_prepare_values(self, project):
        self.ensure_one()
        allocated_hours = 0.0
        if self.product_id.service_type != 'milestones':
            allocated_hours = self._convert_qty_company_hours(self.company_id)
        sale_line_name_parts = self.name.split('\n')

        if sale_line_name_parts and sale_line_name_parts[0] == self.product_id.display_name:
            sale_line_name_parts.pop(0)

        if len(sale_line_name_parts) == 1 and sale_line_name_parts[0]:
            title = sale_line_name_parts[0]
            description = ''
        else:
            title = self.product_id.display_name
            description = '<br/>'.join(sale_line_name_parts)

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

    @api.model
    def _get_product_service_policy(self):
        return ['ordered_prepaid']

    def _prepare_task_template_vals(self, template, project):
        if template.allocated_hours:
            allocated_hours = template.allocated_hours
        else:
            allocated_hours = sum(
                sol._convert_qty_company_hours(self.company_id)
                for sol in self.order_id.order_line
                if sol.product_id.task_template_id.id == template.id
                and sol.product_id.service_policy in self._get_product_service_policy()
            )

        return {
            'name': '%s - %s' % (self.order_id.name, template.name),
            'allocated_hours': allocated_hours,
            'project_id': project.id,
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
        }

    def _get_sale_order_partner_id(self, project):
        return self.order_id.partner_id.id

    def _timesheet_create_task(self, project):
        """ Generate task for the given so line, and link it.
            :param project: record of project.project in which the task should be created
            :return task: record of the created task
        """
        if template := self.product_id.task_template_id:
            vals = self._prepare_task_template_vals(template, project)
            task_id = template.with_context(
                default_partner_id=self._get_sale_order_partner_id(project),
            ).action_create_from_template(vals)
            task = self.env['project.task'].sudo().browse(task_id)
        else:
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
        sale_order_lines = self.filtered(
            lambda sol:
                sol.is_service
                and sol.product_id.service_tracking in ['project_only', 'task_in_project', 'task_global_project']
                and not (sol._is_line_optional() and sol.product_uom_qty == 0)
        )
        so_line_task_global_project = sale_order_lines._get_so_lines_task_global_project()
        so_line_new_project = sale_order_lines._get_so_lines_new_project()
        task_templates = self.env['project.task']

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

        # we store the reference analytic account per SO
        map_account_per_so = {}

        # project_only, task_in_project: create a new project, based or not on a template (1 per SO). May be create a task too.
        # if 'task_in_project' and project_id configured on SO, use that one instead
        for so_line in so_line_new_project.sorted(lambda sol: (sol.sequence, sol.id)):
            project = False
            if so_line.product_id.service_tracking in ['project_only', 'task_in_project']:
                project = so_line.project_id
            if not project and _can_create_project(so_line):
                # If no reference analytic account exists, set the account of the generated project to the account of the project's SO or create a new one
                account = map_account_per_so.get(so_line.order_id.id)
                if not account:
                    account = so_line.order_id.project_account_id or self.env['account.analytic.account'].create(so_line.order_id._prepare_analytic_account_data())
                    map_account_per_so[so_line.order_id.id] = account
                project = so_line.with_context(project_account_id=account.id)._timesheet_create_project()
                # If the SO generates projects on confirmation and the project's SO is not set, set it to the project's SOL with the lowest (sequence, id)
                if not so_line.order_id.project_id:
                    so_line.order_id.project_id = project
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
                if not so_line.task_id and so_line.product_id.task_template_id not in task_templates:
                    task_templates |= so_line.product_id.task_template_id
                    so_line._timesheet_create_task(project=project)
            so_line._handle_milestones(project)

        # task_global_project: if not set, set the project's SO by looking at global projects
        for so_line in so_line_task_global_project.sorted(lambda sol: (sol.sequence, sol.id)):
            if not so_line.order_id.project_id:
                so_line.order_id.project_id = map_sol_project.get(so_line.id)

        # task_global_project: create task in global projects
        for so_line in so_line_task_global_project:
            if not so_line.task_id:
                project = map_sol_project.get(so_line.id) or so_line.order_id.project_id
                if project and so_line.product_uom_qty > 0:
                    if so_line.product_id.task_template_id not in task_templates:
                        task_templates |= so_line.product_id.task_template_id
                        so_line._timesheet_create_task(project)

                elif not project:
                    raise UserError(_(
                        "A project must be defined on the quotation %(order)s or on the form of products creating a task on order.\n"
                        "The following product need a project in which to put its task: %(product_name)s",
                        order=so_line.order_id.name,
                        product_name=so_line.product_id.name,
                    ))

    def _handle_milestones(self, project):
        self.ensure_one()
        if self.product_id.service_policy != 'delivered_milestones':
            return
        if not self.project_id.allow_milestones:
            self.project_id.allow_milestones = True
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
        if not values.get('analytic_distribution') and not self.analytic_distribution:
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

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        if self.order_id.project_id:
            values['project_id'] = self.order_id.project_id.id
        return values
