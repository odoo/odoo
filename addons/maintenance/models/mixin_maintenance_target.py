from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

from .maintenance_order import OPEN_STATES

_debug = DebugLog(__name__)

PROFILE_FACTS = (
    "date_in_service",
    "maintenance_team_id",
    "technician_user_id",
    "expected_mtbf",
)


class MixinMaintenanceTarget(models.AbstractModel):
    """A record that is maintained through its resource. The facts live on the
    resource's maintenance.profile; the host reads them from it and, when
    written, gives the resource its profile."""

    _name = "mixin.maintenance.target"
    _description = "Maintained Resource"

    # The host's slot; every host is a mixin.resource, which declares it fully.
    resource_id = fields.Many2one(comodel_name="resource.resource")
    maintenance_profile_id = fields.Many2one(
        comodel_name="maintenance.profile",
        compute="_compute_maintenance_profile_id",
    )
    maintenance_team_id = fields.Many2one(
        comodel_name="team.team",
        compute="_compute_profile_facts",
        inverse="_inverse_maintenance_team_id",
        search="_search_maintenance_team_id",
        domain=[("use_maintenance", "=", True)],
        check_company=True,
    )
    technician_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Technician",
        compute="_compute_profile_facts",
        inverse="_inverse_technician_user_id",
        search="_search_technician_user_id",
    )
    date_in_service = fields.Date(
        string="In Service Since",
        compute="_compute_profile_facts",
        inverse="_inverse_date_in_service",
    )
    expected_mtbf = fields.Integer(
        string="Expected MTBF",
        compute="_compute_profile_facts",
        inverse="_inverse_expected_mtbf",
    )
    mtbf = fields.Integer(related="resource_id.maintenance_profile_id.mtbf")
    mttr = fields.Integer(related="resource_id.maintenance_profile_id.mttr")
    date_next_failure = fields.Date(
        related="resource_id.maintenance_profile_id.date_next_failure"
    )
    date_last_failure = fields.Date(
        related="resource_id.maintenance_profile_id.date_last_failure"
    )
    maintenance_ids = fields.Many2many(related="resource_id.maintenance_ids")
    maintenance_count = fields.Count(count_of="maintenance_ids")
    maintenance_open_count = fields.Integer(
        string="Current Maintenance",
        compute="_compute_maintenance_open_count",
    )
    maintenance_plan_ids = fields.Many2many(related="resource_id.maintenance_plan_ids")
    maintenance_plan_count = fields.Count(count_of="maintenance_plan_ids")

    @api.depends("resource_id.maintenance_profile_id")
    def _compute_maintenance_profile_id(self):
        for host in self:
            host.maintenance_profile_id = host.resource_id.maintenance_profile_id

    # Dependencies walk the stored link: the profile handle above is computed,
    # and a trigger cannot be inverted through a field the database does not hold.
    @api.depends(
        "resource_id.maintenance_profile_id.date_in_service",
        "resource_id.maintenance_profile_id.maintenance_team_id",
        "resource_id.maintenance_profile_id.technician_user_id",
        "resource_id.maintenance_profile_id.expected_mtbf",
    )
    def _compute_profile_facts(self):
        for host in self:
            profile = host.resource_id.maintenance_profile_id
            for name in PROFILE_FACTS:
                host[name] = profile[name]

    @api.depends("maintenance_ids.state")
    @_debug.perf.timed
    def _compute_maintenance_open_count(self):
        for host in self:
            host.maintenance_open_count = len(
                host.maintenance_ids.filtered(lambda order: order.state in OPEN_STATES)
            )

    def _get_or_create_maintenance_profile(self):
        """The profile is the host's facet: whoever may write the host may give
        its resource a profile, so it is created and written as the system."""
        self.check_singleton()
        profile = self.resource_id.maintenance_profile_id
        if not profile:
            profile = (
                self.env["maintenance.profile"]
                .sudo()
                .create({"resource_id": self.resource_id.id})
            )
            _debug.lifecycle(
                "profile_created", host=self, resource=self.resource_id, profile=profile
            )
            self.resource_id.invalidate_recordset(["maintenance_profile_id"])
            self.invalidate_recordset(["maintenance_profile_id"])
        return profile.sudo()

    def _inverse_profile_fact(self, name):
        for host in self:
            value = host[name]
            profile = host.resource_id.maintenance_profile_id
            if not profile and not value:
                continue
            profile = host._get_or_create_maintenance_profile()
            if profile[name] != value:
                _debug.logic("profile_fact_written", host=host, field=name)
                profile[name] = value

    def _inverse_maintenance_team_id(self):
        self._inverse_profile_fact("maintenance_team_id")

    def _inverse_technician_user_id(self):
        self._inverse_profile_fact("technician_user_id")

    def _inverse_date_in_service(self):
        self._inverse_profile_fact("date_in_service")

    def _inverse_expected_mtbf(self):
        self._inverse_profile_fact("expected_mtbf")

    def _search_maintenance_team_id(self, operator, value):
        return [
            ("resource_id.maintenance_profile_id.maintenance_team_id", operator, value)
        ]

    def _search_technician_user_id(self, operator, value):
        return [
            ("resource_id.maintenance_profile_id.technician_user_id", operator, value)
        ]

    def _get_maintenance_action(self, xmlid):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(xmlid)
        action["domain"] = [("resource_ids", "in", self.resource_id.ids)]
        action["context"] = {
            "default_resource_ids": self.resource_id.ids,
            "default_company_id": self.company_id.id,
            "default_maintenance_team_id": self.maintenance_team_id.id,
        }
        return action

    def action_view_maintenance(self):
        return self._get_maintenance_action("maintenance.maintenance_order_action")

    def action_view_maintenance_plans(self):
        return self._get_maintenance_action("maintenance.maintenance_plan_action")
