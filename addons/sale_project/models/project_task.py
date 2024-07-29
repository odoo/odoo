# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.osv import expression
from odoo.tools import SQL
from odoo.tools.misc import unquote


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _domain_sale_line_id(self):
        domain = expression.AND([
            self.env['sale.order.line']._sellable_lines_domain(),
            self.env['sale.order.line']._domain_sale_line_service(),
            [
                '|',
                ('order_partner_id.commercial_partner_id.id', 'parent_of', unquote('partner_id if partner_id else []')),
                ('order_partner_id', '=?', unquote('partner_id')),
            ],
        ])
        return str(domain)

    sale_order_id = fields.Many2one('sale.order', 'Sales Order', compute='_compute_sale_order_id', store=True, help="Sales order to which the task is linked.", group_expand="_group_expand_sales_order")
    sale_line_id = fields.Many2one(
        'sale.order.line', 'Sales Order Item',
        copy=True, tracking=True, index='btree_not_null', recursive=True,
        compute='_compute_sale_line', store=True, readonly=False,
        domain=_domain_sale_line_id,
        help="Sales Order Item to which the time spent on this task will be added in order to be invoiced to your customer.\n"
             "By default the sales order item set on the project will be selected. In the absence of one, the last prepaid sales order item that has time remaining will be used.\n"
             "Remove the sales order item in order to make this task non billable. You can also change or remove the sales order item of each timesheet entry individually.")
    project_sale_order_id = fields.Many2one('sale.order', string="Project's sale order", related='project_id.sale_order_id')
    sale_order_state = fields.Selection(related='sale_order_id.state')
    task_to_invoice = fields.Boolean("To invoice", compute='_compute_task_to_invoice', search='_search_task_to_invoice', groups='sales_team.group_sale_salesman_all_leads')
    allow_billable = fields.Boolean(related="project_id.allow_billable")
    partner_id = fields.Many2one(inverse='_inverse_partner_id')

    # Project sharing  fields
    display_sale_order_button = fields.Boolean(string='Display Sales Order', compute='_compute_display_sale_order_button')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {'allow_billable', 'sale_order_id', 'sale_line_id', 'display_sale_order_button'}

    @api.model
    def _group_expand_sales_order(self, sales_orders, domain):
        start_date = self._context.get('gantt_start_date')
        scale = self._context.get('gantt_scale')
        if not (start_date and scale):
            return sales_orders
        search_on_comodel = self._search_on_comodel(domain, "sale_order_id", "sale.order")
        if search_on_comodel:
            return search_on_comodel
        return sales_orders

    @api.depends('sale_line_id', 'project_id', 'allow_billable')
    def _compute_sale_order_id(self):
        for task in self:
            if not task.allow_billable:
                task.sale_order_id = False
                continue
            sale_order = (
                task.sale_line_id.order_id
                or task.project_id.sale_order_id
                or task.sale_order_id
            )
            if sale_order and not task.partner_id:
                task.partner_id = sale_order.partner_id
            consistent_partners = (
                sale_order.partner_id
                | sale_order.partner_invoice_id
                | sale_order.partner_shipping_id
            ).commercial_partner_id
            if task.partner_id.commercial_partner_id in consistent_partners:
                task.sale_order_id = sale_order
            else:
                task.sale_order_id = False

    @api.depends('allow_billable')
    def _compute_partner_id(self):
        billable_task = self.filtered(lambda t: t.allow_billable or (not self._origin and t.parent_id.allow_billable))
        (self - billable_task).partner_id = False
        super(ProjectTask, billable_task)._compute_partner_id()

    def _inverse_partner_id(self):
        for task in self:
            # check that sale_line_id/sale_order_id and customer are consistent
            consistent_partners = (
                task.sale_order_id.partner_id
                | task.sale_order_id.partner_invoice_id
                | task.sale_order_id.partner_shipping_id
            ).commercial_partner_id
            if task.sale_order_id and task.partner_id.commercial_partner_id not in consistent_partners:
                task.sale_order_id = task.sale_line_id = False

    @api.depends('sale_line_id.order_partner_id', 'parent_id.sale_line_id', 'project_id.sale_line_id', 'milestone_id.sale_line_id', 'allow_billable')
    def _compute_sale_line(self):
        for task in self:
            if not (task.allow_billable or task.parent_id.allow_billable):
                task.sale_line_id = False
                continue
            if not task.sale_line_id:
                # if the project_id is set then it means the task is classic task or a subtask with another project than its parent.
                # To determine the sale_line_id, we first need to look at the parent before the project to manage the case of subtasks.
                # Two sub-tasks in the same project do not necessarily have the same sale_line_id (need to look at the parent task).
                sale_line = False
                if task.parent_id.sale_line_id and task.parent_id.partner_id.commercial_partner_id == task.partner_id.commercial_partner_id:
                    sale_line = task.parent_id.sale_line_id
                elif task.project_id.sale_line_id and task.project_id.partner_id.commercial_partner_id == task.partner_id.commercial_partner_id:
                    sale_line = task.project_id.sale_line_id
                task.sale_line_id = sale_line or task.milestone_id.sale_line_id

    @api.depends('sale_order_id')
    def _compute_display_sale_order_button(self):
        if not self.sale_order_id:
            self.display_sale_order_button = False
            return
        try:
            sale_orders = self.env['sale.order'].search([('id', 'in', self.sale_order_id.ids)])
            for task in self:
                task.display_sale_order_button = task.sale_order_id in sale_orders
        except AccessError:
            self.display_sale_order_button = False

    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for task in self.sudo():
            if task.sale_line_id:
                if not task.sale_line_id.is_service or task.sale_line_id.is_expense:
                    raise ValidationError(_(
                        'You cannot link the order item %(order_id)s - %(product_id)s to this task because it is a re-invoiced expense.',
                        order_id=task.sale_line_id.order_id.name,
                        product_id=task.sale_line_id.product_id.display_name,
                    ))

    # ---------------------------------------------------
    # Actions
    # ---------------------------------------------------

    def _get_action_view_so_ids(self):
        return self.sale_order_id.ids

    def action_view_so(self):
        so_ids = self._get_action_view_so_ids()
        action_window = {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "name": _("Sales Order"),
            "views": [[False, "list"], [False, "kanban"], [False, "form"]],
            "context": {"create": False, "show_sale": True},
            "domain": [["id", "in", so_ids]],
        }
        if len(so_ids) == 1:
            action_window["views"] = [[False, "form"]]
            action_window["res_id"] = so_ids[0]

        return action_window

    def action_project_sharing_view_so(self):
        self.ensure_one()
        if not self.display_sale_order_button:
            return {}
        return {
            "name": "Portal Sale Order",
            "type": "ir.actions.act_url",
            "url": self.sale_order_id.access_url,
        }

    def _rating_get_partner(self):
        partner = self.partner_id or self.sale_line_id.order_id.partner_id
        return partner or super()._rating_get_partner()

    @api.depends('sale_order_id.invoice_status', 'sale_order_id.order_line')
    def _compute_task_to_invoice(self):
        for task in self:
            if task.sale_order_id:
                task.task_to_invoice = bool(task.sale_order_id.invoice_status not in ('no', 'invoiced'))
            else:
                task.task_to_invoice = False

    @api.model
    def _search_task_to_invoice(self, operator, value):
        sql = SQL("""(
            SELECT so.id
            FROM sale_order so
            WHERE so.invoice_status != 'invoiced'
                AND so.invoice_status != 'no'
        )""")
        operator_new = 'in'
        if (bool(operator == '=') ^ bool(value)):
            operator_new = 'not in'
        return [('sale_order_id', operator_new, sql)]

    @api.onchange('sale_line_id')
    def _onchange_partner_id(self):
        if not self.partner_id and self.sale_line_id:
            self.partner_id = self.sale_line_id.order_partner_id

    def _get_projects_to_make_billable_domain(self, additional_domain=None):
        return expression.AND([
            super()._get_projects_to_make_billable_domain(additional_domain),
            [
                ('partner_id', '!=', False),
                ('allow_billable', '=', False),
                ('project_id', '!=', False),
            ],
        ])
