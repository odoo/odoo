from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.translate import LazyTranslate

from odoo.addons.team.models.team import TeamUsage

_lt = LazyTranslate(__name__)


class TeamTeam(models.Model):
    _inherit = "team.team"

    use_maintenance = fields.Boolean(
        string="Maintenance",
        help="The team repairs and maintains equipment: it receives maintenance orders.",
    )
    maintenance_order_ids = fields.One2many(
        comodel_name="maintenance.order",
        inverse_name="maintenance_team_id",
        copy=False,
    )
    maintenance_todo_order_count = fields.Integer(
        string="Number of Orders",
        compute="_compute_maintenance_todo_orders",
    )
    maintenance_todo_order_count_scheduled = fields.Integer(
        string="Number of Orders Scheduled",
        compute="_compute_maintenance_todo_orders",
    )
    maintenance_todo_order_count_high_priority = fields.Integer(
        string="Number of Orders in High Priority",
        compute="_compute_maintenance_todo_orders",
    )
    maintenance_todo_order_count_block = fields.Integer(
        string="Number of Orders Blocked",
        compute="_compute_maintenance_todo_orders",
    )
    maintenance_todo_order_count_unscheduled = fields.Integer(
        string="Number of Orders Unscheduled",
        compute="_compute_maintenance_todo_orders",
    )
    maintenance_alias_id = fields.Many2one(
        comodel_name="team.alias",
        string="Maintenance Alias",
        compute="_compute_maintenance_alias_id",
        search="_search_maintenance_alias_id",
        help="Email alias for this maintenance team.",
    )
    maintenance_alias_name = fields.Char(
        related="maintenance_alias_id.alias_name",
        string="Maintenance Alias Name",
        readonly=False,
    )
    maintenance_alias_domain_id = fields.Many2one(
        related="maintenance_alias_id.alias_domain_id",
        string="Maintenance Alias Domain",
        readonly=False,
    )
    maintenance_alias_email = fields.Char(
        related="maintenance_alias_id.alias_full_name",
        string="Maintenance Email Alias",
    )

    @api.depends("alias_ids.usage")
    def _compute_maintenance_alias_id(self):
        self._compute_usage_alias_field("maintenance", "maintenance_alias_id")

    @api.depends("maintenance_order_ids.state")
    def _compute_maintenance_todo_orders(self):
        Order = self.env["maintenance.order"]
        data_by_team = defaultdict(list)
        for team, *row in Order._read_group(
            [("maintenance_team_id", "in", self.ids), *Order._get_domain_open()],
            [
                "maintenance_team_id",
                "date_scheduled_start:year",
                "priority",
                "kanban_state",
            ],
            ["__count"],
        ):
            data_by_team[team].append(row)
        for team in self:
            data = data_by_team[team]
            team.maintenance_todo_order_count = sum(count for (_, _, _, count) in data)
            team.maintenance_todo_order_count_scheduled = sum(
                count
                for (date_scheduled_start, _, _, count) in data
                if date_scheduled_start
            )
            team.maintenance_todo_order_count_high_priority = sum(
                count for (_, priority, _, count) in data if priority == "3"
            )
            team.maintenance_todo_order_count_block = sum(
                count
                for (_, _, kanban_state, count) in data
                if kanban_state == "blocked"
            )
            team.maintenance_todo_order_count_unscheduled = (
                team.maintenance_todo_order_count
                - team.maintenance_todo_order_count_scheduled
            )

    def _search_maintenance_alias_id(self, operator, value):
        return self._search_usage_alias_field("maintenance", operator, value)

    @api.model
    def _get_usages(self):
        return super()._get_usages() | {
            "maintenance": TeamUsage(
                key="maintenance",
                flag="use_maintenance",
                label=_lt("Maintenance"),
                manager_group="maintenance.group_equipment_manager",
                alias_model="maintenance.order",
            ),
        }

    def _prepare_usage_alias_defaults(self, key):
        defaults = super()._prepare_usage_alias_defaults(key)
        if key == "maintenance":
            defaults["maintenance_team_id"] = defaults.pop("team_id")
        return defaults
