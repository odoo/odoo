# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _get_default_partner_id(self, project, parent):
        res = super()._get_default_partner_id(project, parent)
        if not res and project:
            # project in sudo if the current user is a portal user.
            related_project = project
            if self.env.user._is_portal() and not self.env.user._is_internal():
                related_project = related_project.sudo()
            if related_project.pricing_type == 'employee_rate':
                return related_project.sale_line_employee_ids.sale_line_id.order_partner_id[:1]
        return res

    sale_order_id = fields.Many2one(domain="['|', '|', ('partner_id', '=', partner_id), ('partner_id.commercial_partner_id.id', 'parent_of', partner_id), ('partner_id', 'parent_of', partner_id)]")
    pricing_type = fields.Selection(related="project_id.pricing_type")
    is_project_map_empty = fields.Boolean("Is Project map empty", compute='_compute_is_project_map_empty')
    has_multi_sol = fields.Boolean(compute='_compute_has_multi_sol', compute_sudo=True)
    timesheet_product_id = fields.Many2one(related="project_id.timesheet_product_id")
    remaining_hours_so = fields.Float('Time Remaining on SO', compute='_compute_remaining_hours_so', search='_search_remaining_hours_so', compute_sudo=True)
    remaining_hours_available = fields.Boolean(related="sale_line_id.remaining_hours_available")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {
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

    @api.model
    def _search_remaining_hours_so(self, operator, value):
        return [('sale_line_id.remaining_hours', operator, value)]

    def _inverse_partner_id(self):
        super()._inverse_partner_id()
        for task in self:
            if task.allow_billable and not task.sale_line_id:
                task.sale_line_id = task.sudo()._get_last_sol_of_customer()

    @api.depends('sale_line_id.order_partner_id', 'parent_id.sale_line_id', 'project_id.sale_line_id', 'allow_billable')
    def _compute_sale_line(self):
        super()._compute_sale_line()
        for task in self:
            if task.allow_billable and not task.sale_line_id:
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
        if not self.partner_id.commercial_partner_id or not self.allow_billable:
            return False
        SaleOrderLine = self.env['sale.order.line']
        domain = expression.AND([
            SaleOrderLine._domain_sale_line_service(),
            [
                ('company_id', '=?', self.company_id.id),
                ('order_partner_id', 'child_of', self.partner_id.commercial_partner_id.ids),
                ('remaining_hours', '>', 0),
            ],
        ])
        if self.project_id.pricing_type != 'task_rate' and self.project_sale_order_id and self.partner_id.commercial_partner_id == self.project_id.partner_id.commercial_partner_id:
            domain = expression.AND([domain, [('order_id', '=?', self.project_sale_order_id.id)]])
        return SaleOrderLine.search(domain, limit=1)

    def _get_timesheet(self):
        # return not invoiced timesheet and timesheet without so_line or so_line linked to task
        timesheet_ids = super()._get_timesheet()
        return timesheet_ids.filtered(lambda t: t._is_not_billed())

    def _get_action_view_so_ids(self):
        return list(set((self.sale_order_id + self.timesheet_ids.so_line.order_id).ids))
