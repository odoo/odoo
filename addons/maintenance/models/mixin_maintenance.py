from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from .maintenance_order import OPEN_STATES


class MixinMaintenance(models.AbstractModel):
    _name = "mixin.maintenance"
    _check_company_auto = True
    _description = "Maintenance Maintained Item"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    date_effective = fields.Date(
        string="Effective Date",
        default=fields.Date.context_today,
        required=True,
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
    maintenance_ids = fields.One2many(
        comodel_name="maintenance.order"
    )  # needs to be extended in order to specify inverse_name !
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
    estimated_next_failure = fields.Date(
        string="Estimated time before next failure (in days)",
        compute="_compute_maintenance_order",
        help="Computed as Latest Failure Date + MTBF",
    )
    latest_failure_date = fields.Date(compute="_compute_maintenance_order")

    @api.depends("company_id")
    def _compute_maintenance_team_id(self):
        for record in self:
            if (
                record.maintenance_team_id.company_id
                and record.maintenance_team_id.company_id.id != record.company_id.id
            ):
                record.maintenance_team_id = False

    @api.depends(
        "date_effective",
        "maintenance_ids.maintenance_type",
        "maintenance_ids.state",
        "maintenance_ids.close_date",
        "maintenance_ids.date_order",
    )
    def _compute_maintenance_order(self):
        for record in self:
            maintenance_orders = record.maintenance_ids.filtered(
                lambda mr: mr.maintenance_type == "corrective" and mr.state == "done"
            )
            repair_days = [
                (order.close_date - order.date_order).days
                for order in maintenance_orders
                if order.close_date and order.date_order
            ]
            record.mttr = sum(repair_days) / len(repair_days) if repair_days else 0
            record.latest_failure_date = max(
                (order.date_order for order in maintenance_orders),
                default=False,
            )
            record.mtbf = (
                record.latest_failure_date
                and max((record.latest_failure_date - record.date_effective).days, 0)
                / len(maintenance_orders)
            ) or 0
            record.estimated_next_failure = (
                record.mtbf
                and record.latest_failure_date + relativedelta(days=record.mtbf)
            ) or False

    @api.depends("maintenance_ids.state")
    def _compute_maintenance_open_count(self):
        for record in self:
            record.maintenance_open_count = len(
                record.maintenance_ids.filtered(lambda mr: mr.state in OPEN_STATES)
            )
