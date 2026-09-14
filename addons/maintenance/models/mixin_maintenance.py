from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


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
        store=True,
        index="btree_not_null",
        readonly=False,
        domain=[("use_maintenance", "=", True)],
        check_company=True,
    )
    technician_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Technician",
        tracking=True,
    )
    maintenance_ids = fields.One2many(
        comodel_name="maintenance.request"
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
        compute="_compute_maintenance_request",
        help="Mean Time Between Failure, computed based on done corrective maintenances.",
    )
    mttr = fields.Integer(
        string="MTTR",
        compute="_compute_maintenance_request",
        help="Mean Time To Repair",
    )
    estimated_next_failure = fields.Date(
        string="Estimated time before next failure (in days)",
        compute="_compute_maintenance_request",
        help="Computed as Latest Failure Date + MTBF",
    )
    latest_failure_date = fields.Date(compute="_compute_maintenance_request")

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
        "maintenance_ids.stage_id.done",
        "maintenance_ids.close_date",
        "maintenance_ids.request_date",
    )
    def _compute_maintenance_request(self):
        for record in self:
            maintenance_requests = record.maintenance_ids.filtered(
                lambda mr: mr.maintenance_type == "corrective" and mr.stage_id.done
            )
            repair_days = [
                (request.close_date - request.request_date).days
                for request in maintenance_requests
                if request.close_date and request.request_date
            ]
            record.mttr = sum(repair_days) / len(repair_days) if repair_days else 0
            record.latest_failure_date = max(
                (request.request_date for request in maintenance_requests),
                default=False,
            )
            record.mtbf = (
                record.latest_failure_date
                and max((record.latest_failure_date - record.date_effective).days, 0)
                / len(maintenance_requests)
            ) or 0
            record.estimated_next_failure = (
                record.mtbf
                and record.latest_failure_date + relativedelta(days=record.mtbf)
            ) or False

    @api.depends("maintenance_ids.stage_id.done", "maintenance_ids.archive")
    def _compute_maintenance_open_count(self):
        for record in self:
            record.maintenance_open_count = len(
                record.maintenance_ids.filtered(
                    lambda mr: not mr.stage_id.done and not mr.archive
                )
            )
