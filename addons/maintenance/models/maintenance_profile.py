from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MaintenanceProfile(models.Model):
    """What maintenance knows about one resource: who maintains it, since when,
    and what its failures say. A facet of the resource, one per resource,
    created the first time a host writes one of its facts."""

    _name = "maintenance.profile"
    _description = "Maintenance Profile"
    _rec_name = "resource_id"

    resource_id = fields.Many2one(
        comodel_name="resource.resource",
        index="unique",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="resource_id.company_id",
        precompute=True,
        store=True,
    )
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
    expected_mtbf = fields.Integer(
        string="Expected MTBF",
        help="Expected Mean Time Between Failure",
    )
    mtbf = fields.Integer(
        string="MTBF",
        compute="_compute_reliability",
        help="Mean Time Between Failure, computed based on done corrective maintenances.",
    )
    mttr = fields.Integer(
        string="MTTR",
        compute="_compute_reliability",
        help="Mean Time To Repair",
    )
    date_next_failure = fields.Date(
        string="Estimated Next Failure",
        compute="_compute_reliability",
        help="Computed as Last Failure + MTBF",
    )
    date_last_failure = fields.Date(
        string="Last Failure",
        compute="_compute_reliability",
    )

    @api.depends("company_id")
    def _compute_maintenance_team_id(self):
        for profile in self:
            team = profile.maintenance_team_id
            if team.company_id and team.company_id != profile.company_id:
                _debug.logic(
                    "team_cleared", reason="other_company", profile=profile, team=team
                )
                profile.maintenance_team_id = False

    @api.depends(
        "date_in_service",
        "resource_id.maintenance_ids.maintenance_type",
        "resource_id.maintenance_ids.state",
        "resource_id.maintenance_ids.date_done",
        "resource_id.maintenance_ids.date_confirmed",
    )
    @_debug.perf.timed
    def _compute_reliability(self):
        for profile in self:
            orders = profile.resource_id.maintenance_ids.filtered(
                lambda order: (
                    order.maintenance_type == "corrective" and order.state == "done"
                )
            )
            failure_days = {
                order: fields.Datetime.context_timestamp(
                    order, order.date_confirmed
                ).date()
                for order in orders
                if order.date_confirmed
            }
            repair_days = [
                (order.date_done - failure_day).days
                for order, failure_day in failure_days.items()
                if order.date_done
            ]
            profile.mttr = sum(repair_days) / len(repair_days) if repair_days else 0
            profile.date_last_failure = max(failure_days.values(), default=False)
            since = profile.date_in_service or (
                profile.create_date and profile.create_date.date()
            )
            profile.mtbf = (
                profile.date_last_failure
                and since
                and max((profile.date_last_failure - since).days, 0) / len(orders)
            ) or 0
            profile.date_next_failure = (
                profile.mtbf
                and profile.date_last_failure + relativedelta(days=profile.mtbf)
            ) or False
