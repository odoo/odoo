from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from .maintenance_order import OPEN_STATES


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    date_in_service = fields.Date(
        string="In Service Since",
        default=fields.Date.context_today,
        help="This date will be used to compute the Mean Time Between Failure.",
    )
    maintenance_team_id = fields.Many2one(
        comodel_name="team.team",
        compute="_compute_maintenance_team_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
        domain=[("use_maintenance", "=", True)],
        check_company=True,
    )
    technician_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Technician",
    )
    maintenance_ids = fields.Many2many(
        comodel_name="maintenance.order",
        relation="maintenance_order_resource_rel",
        column1="resource_id",
        column2="order_id",
    )
    maintenance_count = fields.Count(
        count_of="maintenance_ids",
        store=True,
    )
    maintenance_open_count = fields.Integer(
        string="Current Maintenance",
        compute="_compute_maintenance_open_count",
        store=True,
    )
    expected_mtbf = fields.Integer(
        string="Expected MTBF",
        help="Expected Mean Time Between Failure",
    )
    mtbf = fields.Integer(
        string="MTBF",
        compute="_compute_maintenance_order",
        help="Mean Time Between Failure, computed based on done corrective maintenances.",
    )
    mttr = fields.Integer(
        string="MTTR",
        compute="_compute_maintenance_order",
        help="Mean Time To Repair",
    )
    date_next_failure = fields.Date(
        string="Estimated Next Failure",
        compute="_compute_maintenance_order",
        help="Computed as Last Failure + MTBF",
    )
    date_last_failure = fields.Date(
        string="Last Failure",
        compute="_compute_maintenance_order",
    )
    maintenance_plan_ids = fields.Many2many(
        comodel_name="maintenance.plan",
        relation="maintenance_plan_resource_rel",
        column1="resource_id",
        column2="plan_id",
    )
    maintenance_plan_count = fields.Count(count_of="maintenance_plan_ids")

    @api.depends("company_id")
    def _compute_maintenance_team_id(self):
        for record in self:
            if (
                record.maintenance_team_id.company_id
                and record.maintenance_team_id.company_id.id != record.company_id.id
            ):
                record.maintenance_team_id = False

    @api.depends(
        "date_in_service",
        "maintenance_ids.maintenance_type",
        "maintenance_ids.state",
        "maintenance_ids.date_done",
        "maintenance_ids.date_confirmed",
    )
    def _compute_maintenance_order(self):
        for record in self:
            maintenance_orders = record.maintenance_ids.filtered(
                lambda mr: mr.maintenance_type == "corrective" and mr.state == "done"
            )
            failure_days = {
                order: fields.Datetime.context_timestamp(
                    order, order.date_confirmed
                ).date()
                for order in maintenance_orders
                if order.date_confirmed
            }
            repair_days = [
                (order.date_done - failure_day).days
                for order, failure_day in failure_days.items()
                if order.date_done
            ]
            record.mttr = sum(repair_days) / len(repair_days) if repair_days else 0
            record.date_last_failure = max(failure_days.values(), default=False)
            since = record.date_in_service or (
                record.create_date and record.create_date.date()
            )
            record.mtbf = (
                record.date_last_failure
                and since
                and max((record.date_last_failure - since).days, 0)
                / len(maintenance_orders)
            ) or 0
            record.date_next_failure = (
                record.mtbf
                and record.date_last_failure + relativedelta(days=record.mtbf)
            ) or False

    @api.depends("maintenance_ids.state")
    def _compute_maintenance_open_count(self):
        for record in self:
            record.maintenance_open_count = len(
                record.maintenance_ids.filtered(lambda mr: mr.state in OPEN_STATES)
            )
