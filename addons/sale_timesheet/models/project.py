# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = 'project.project'

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Item', domain="[('is_expense', '=', False), ('order_id', '=', sale_order_id), ('state', 'in', ['sale', 'done'])]", copy=False, help="Sale order line from which the project has been created. Used for tracability.")
    sale_order_id = fields.Many2one('sale.order', 'Sales Order', domain="[('partner_id', '=', partner_id)]", readonly=True, copy=False)
    billable_type = fields.Selection([
        ('task_rate', 'At Task Rate'),
        ('employee_rate', 'At Employee Rate'),
        ('no', 'No Billable')
    ], string="Billable Type", compute='_compute_billable_type', compute_sudo=True, store=True,
        help='Billable type implies:\n'
        ' - At task rate: each time spend on a task is billed at task rate.\n'
        ' - At employee rate: each employee log time billed at his rate.\n'
        ' - No Billable: track time without invoicing it')
    sale_line_employee_ids = fields.One2many('project.sale.line.employee.map', 'project_id', "Sale line/Employee map", copy=False)

    _sql_constraints = [
        ('sale_order_required_if_sale_line', "CHECK((sale_line_id IS NOT NULL AND sale_order_id IS NOT NULL) OR (sale_line_id IS NULL))", 'The Project should be linked to a Sale Order to select an Sale Order Items.'),
    ]

    @api.depends('sale_order_id', 'sale_line_id', 'sale_line_employee_ids')
    def _compute_billable_type(self):
        for project in self:
            billable_type = 'no'
            if project.sale_order_id:
                if project.sale_line_employee_ids:
                    billable_type = 'employee_rate'
                else:
                    billable_type = 'task_rate'
            project.billable_type = billable_type

    @api.onchange('sale_line_employee_ids', 'billable_type')
    def _onchange_sale_line_employee_ids(self):
        if self.billable_type == 'task_rate':
            if self.sale_line_employee_ids:
                self.billable_type = 'employee_rate'
        else:
            if self.billable_type == 'no':
                self.sale_line_employee_ids = False

    @api.constrains('sale_line_id', 'billable_type')
    def _check_sale_line_type(self):
        for project in self:
            if project.billable_type == 'task_rate':
                if project.sale_line_id and not project.sale_line_id.is_service:
                    raise ValidationError(_("A billable project should be linked to a Sales Order Item having a Service product."))
                if project.sale_line_id and project.sale_line_id.is_expense:
                    raise ValidationError(_("A billable project should be linked to a Sales Order Item that does not come from an expense or a vendor bill."))

    @api.multi
    def action_view_timesheet(self):
        self.ensure_one()
        if self.allow_timesheets:
            return self.action_view_timesheet_plan()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheets of %s') % self.name,
            'domain': [('project_id', '!=', False)],
            'res_model': 'account.analytic.line',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
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

    @api.multi
    def action_view_timesheet_plan(self):
        action = self.env.ref('sale_timesheet.project_timesheet_action_client_timesheet_plan').read()[0]
        action['params'] = {
            'project_ids': self.ids,
        }
        action['context'] = {
            'active_id': self.id,
            'active_ids': self.ids,
            'search_default_display_name': self.name,
        }
        return action

    @api.multi
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
            },
        }

    @api.model
    def _map_tasks_default_valeus(self, task):
        defaults = super(Project, self)._map_tasks_default_valeus(task)
        defaults['sale_line_id'] = False
        return defaults


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model
    def _get_default_partner(self):
        partner = False
        if 'default_project_id' in self.env.context:  # partner from SO line is prior on one from project
            project_sudo = self.env['project.project'].browse(self.env.context['default_project_id']).sudo()
            partner = project_sudo.sale_line_id.order_partner_id
        if not partner:
            partner = super(ProjectTask, self)._get_default_partner()
        return partner

    @api.model
    def _default_sale_line_id(self):
        sale_line_id = False
        if self._context.get('default_parent_id'):
            parent_task = self.env['project.task'].browse(self._context['default_parent_id'])
            sale_line_id = parent_task.sale_line_id.id
        if not sale_line_id and self._context.get('default_project_id'):
            project = self.env['project.project'].browse(self.env.context['default_project_id'])
            if project.billable_type != 'no':
                sale_line_id = project.sale_line_id.id
        return sale_line_id

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Item', default=_default_sale_line_id, domain="[('is_service', '=', True), ('order_partner_id', '=', partner_id), ('is_expense', '=', False), ('state', 'in', ['sale', 'done'])]")
    sale_order_id = fields.Many2one('sale.order', 'Sales Order', compute='_compute_sale_order_id', compute_sudo=True, store=True, readonly=True)
    billable_type = fields.Selection([
        ('task_rate', 'At Task Rate'),
        ('employee_rate', 'At Employee Rate'),
        ('no', 'No Billable')
    ], string="Billable Type", compute='_compute_billable_type', compute_sudo=True, store=True)
    is_project_map_empty = fields.Boolean("Is Project map empty", compute='_compute_is_project_map_empty')

    @api.multi
    @api.depends('sale_line_id', 'project_id', 'billable_type')
    def _compute_sale_order_id(self):
        for task in self:
            if task.billable_type == 'task_rate':
                task.sale_order_id = task.sale_line_id.sudo().order_id or task.project_id.sale_order_id
            elif task.billable_type == 'employee_rate':
                task.sale_order_id = task.project_id.sale_order_id
            elif task.billable_type == 'no':
                task.sale_order_id = False

    @api.multi
    @api.depends('project_id.billable_type', 'sale_line_id')
    def _compute_billable_type(self):
        for task in self:
            billable_type = 'no'
            if task.project_id.billable_type == 'employee_rate':
                billable_type = task.project_id.billable_type
            elif (task.project_id.billable_type in ['task_rate', 'no'] and task.sale_line_id):  # create a task in global project (non billable)
                billable_type = 'task_rate'
            task.billable_type = billable_type

    @api.depends('project_id.sale_line_employee_ids')
    def _compute_is_project_map_empty(self):
        for task in self:
            task.is_project_map_empty = not bool(task.sudo().project_id.sale_line_employee_ids)

    @api.onchange('project_id')
    def _onchange_project(self):
        result = super(ProjectTask, self)._onchange_project()
        self.sale_line_id = self.project_id.sale_line_id
        if not self.parent_id and not self.partner_id:
            self.partner_id = self.sale_line_id.order_partner_id
        # set domain on SO: on non billable project, all SOL of customer, otherwise the one from the SO
        result = result or {}
        domain = [('is_service', '=', True), ('is_expense', '=', False), ('order_partner_id', 'child_of', self.partner_id.commercial_partner_id.id), ('state', 'in', ['sale', 'done'])]
        if self.project_id.sale_order_id:
            domain += [('order_id', '=', self.project_id.sale_order_id.id)]
        result.setdefault('domain', {})['sale_line_id'] = domain
        return result

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        result = super(ProjectTask, self)._onchange_partner_id()
        result = result or {}
        if self.sale_line_id.order_partner_id.commercial_partner_id != self.partner_id.commercial_partner_id:
            self.sale_line_id = False
        if self.partner_id:
            result.setdefault('domain', {})['sale_line_id'] = [('is_service', '=', True), ('is_expense', '=', False), ('order_partner_id', 'child_of', self.partner_id.commercial_partner_id.id), ('state', 'in', ['sale', 'done'])]
        return result

    @api.multi
    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for task in self.sudo():
            if task.sale_line_id:
                if not task.sale_line_id.is_service or task.sale_line_id.is_expense:
                    raise ValidationError(_('You cannot link the order item %s - %s to this task because it is a re-invoiced expense.' % (task.sale_line_id.order_id.id, task.sale_line_id.product_id.name)))

    @api.multi
    def write(self, values):
        if values.get('project_id'):
            project_dest = self.env['project.project'].browse(values['project_id'])
            if project_dest.billable_type == 'employee_rate':
                values['sale_line_id'] = False
        return super(ProjectTask, self).write(values)

    @api.multi
    def unlink(self):
        if any(task.sale_line_id for task in self):
            raise ValidationError(_('You have to unlink the task from the sale order item in order to delete it.'))
        return super(ProjectTask, self).unlink()

    # ---------------------------------------------------
    # Subtasks
    # ---------------------------------------------------

    @api.model
    def _subtask_implied_fields(self):
        result = super(ProjectTask, self)._subtask_implied_fields()
        return result + ['sale_line_id']

    def _subtask_write_values(self, values):
        result = super(ProjectTask, self)._subtask_write_values(values)
        # changing the partner on a task will reset the sale line of its subtasks
        # if a sale line is not beeing set
        if 'partner_id' in result and 'sale_line_id' not in result:
            result['sale_line_id'] = False
        elif 'sale_line_id' in result:
            result.pop('sale_line_id')
        return result

    # ---------------------------------------------------
    # Actions
    # ---------------------------------------------------

    @api.multi
    def action_view_so(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_order_id.id,
            "context": {"create": False, "show_sale": True},
        }

    def rating_get_partner_id(self):
        partner = self.partner_id or self.sale_line_id.order_id.partner_id
        if partner:
            return partner
        return super(ProjectTask, self).rating_get_partner_id()
