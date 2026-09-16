from odoo import api, fields, models
from odoo.fields import Domain


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = "project.task"

    def _get_default_partner_id(self, project=None, parent=None):
        res = super()._get_default_partner_id(project, parent)
        if not res and project:
            related_project = project
            if self.env.user._is_portal() and not self.env.user._is_internal():
                related_project = related_project.sudo()
            if related_project.pricing_type == "employee_rate":
                return related_project.sale_line_employee_ids.sale_line_id.partner_id[
                    :1
                ]
        return res

    sale_order_id = fields.Many2one(
        domain="['|', '|', ('partner_id', '=', partner_id), ('partner_id.commercial_partner_id.id', 'parent_of', partner_id), ('partner_id', 'parent_of', partner_id)]"
    )
    pricing_type = fields.Selection(related="project_id.pricing_type")
    is_project_map_empty = fields.Boolean(
        string="Is Project map empty",
        compute="_compute_is_project_map_empty",
    )
    has_multi_sol = fields.Boolean(
        compute="_compute_has_multi_sol",
        compute_sudo=True,
    )
    timesheet_product_id = fields.Many2one(related="project_id.timesheet_product_id")
    remaining_hours_so = fields.Float(
        string="Time Remaining on SO",
        compute="_compute_remaining_hours_so",
        search="_search_remaining_hours_so",
        compute_sudo=True,
    )
    remaining_hours_available = fields.Boolean(
        related="sale_line_id.remaining_hours_available"
    )
    last_sol_of_customer = fields.Many2one(
        comodel_name="sale.order.line",
        compute="_compute_last_sol_of_customer",
    )

    @property
    def TASK_PORTAL_READABLE_FIELDS(self):
        return super().TASK_PORTAL_READABLE_FIELDS | {
            "remaining_hours_available",
            "remaining_hours_so",
        }

    @api.depends("sale_line_id", "timesheet_ids", "timesheet_ids.unit_amount")
    def _compute_remaining_hours_so(self):
        timesheets = self.timesheet_ids.filtered(
            lambda t: (
                t.task_id.sale_line_id in (t.so_line, t._origin.so_line)
                and t.so_line.remaining_hours_available
            )
        )

        mapped_remaining_hours = {
            task._origin.id: (task.sale_line_id and task.sale_line_id.remaining_hours)
            or 0.0
            for task in self
        }
        uom_hour = self.env.ref("uom.product_uom_hour")
        for timesheet in timesheets:
            delta = 0
            if timesheet._origin.so_line == timesheet.task_id.sale_line_id:
                delta += timesheet._origin.unit_amount
            if timesheet.so_line == timesheet.task_id.sale_line_id:
                delta -= timesheet.unit_amount
            if delta:
                mapped_remaining_hours[timesheet.task_id._origin.id] += (
                    timesheet.product_uom_id._get_quantity_in_unit(
                        delta, uom_hour, raise_if_failure=False
                    )
                )

        for task in self:
            task.remaining_hours_so = mapped_remaining_hours[task._origin.id]

    @api.model
    def _search_remaining_hours_so(self, operator, value):
        return [("sale_line_id.remaining_hours", operator, value)]

    def _compute_last_sol_of_customer(self):
        sol_per_domain = {}
        for task in self:
            domain = tuple(task._get_domain_last_sol_of_customer())
            if not domain:
                task.last_sol_of_customer = False
                continue
            if domain not in sol_per_domain:
                sol_per_domain[domain] = self.env["sale.order.line"].search(  # noqa: E8507 - one query per distinct domain, cached across tasks
                    domain, limit=1
                )
            task.last_sol_of_customer = sol_per_domain[domain]

    def _inverse_partner_id(self):
        super()._inverse_partner_id()
        for task in self:
            if task.allow_billable and not task.sale_line_id:
                task.sale_line_id = task.sudo().last_sol_of_customer

    @api.depends(
        "sale_line_id.partner_id",
        "parent_id.sale_line_id",
        "project_id.sale_line_id",
        "allow_billable",
    )
    def _compute_sale_line_id(self):
        super()._compute_sale_line_id()
        for task in self:
            if task.allow_billable and not task.sale_line_id:
                task.sale_line_id = task.last_sol_of_customer

    @api.depends("project_id.sale_line_employee_ids")
    def _compute_is_project_map_empty(self):
        for task in self:
            task.is_project_map_empty = not bool(
                task.sudo().project_id.sale_line_employee_ids
            )

    @api.depends("timesheet_ids")
    def _compute_has_multi_sol(self):
        for task in self:
            task.has_multi_sol = (
                task.timesheet_ids and task.timesheet_ids.so_line != task.sale_line_id
            )

    def _get_domain_last_sol_of_customer(self):
        self.check_singleton()
        if not self.partner_id.commercial_partner_id or not self.allow_billable:
            return []
        SaleOrderLine = self.env["sale.order.line"]
        domain = Domain.AND(
            [
                SaleOrderLine._domain_sale_line_service(),
                [
                    ("company_id", "=?", self.company_id.id),
                    (
                        "partner_id",
                        "child_of",
                        self.partner_id.commercial_partner_id.id,
                    ),
                    ("remaining_hours", ">", 0),
                ],
            ]
        )
        if (
            self.project_id.pricing_type != "task_rate"
            and self.project_sale_order_id
            and self.partner_id.commercial_partner_id
            == self.project_id.partner_id.commercial_partner_id
        ):
            domain &= Domain("order_id", "=", self.project_sale_order_id.id)
        return domain

    def _get_timesheet(self):
        timesheet_ids = super()._get_timesheet()
        return timesheet_ids.filtered(lambda t: t._is_not_billed())

    def _get_action_view_so_ids(self):
        return list(set((self.sale_order_id + self.timesheet_ids.so_line.order_id).ids))
