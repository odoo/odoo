import datetime
from ast import literal_eval

from odoo import _, api, exceptions, fields, models
from odoo.tools import float_round


class TeamMember(models.Model):
    _inherit = "team.member"

    team_use_sale = fields.Boolean(related="team_id.use_sale")
    lead_assignment_enabled = fields.Boolean(related="team_id.lead_assignment_enabled")
    lead_assignment_domain = fields.Char(tracking=True)
    lead_assignment_domain_preferred = fields.Char(
        string="Preference assignment Domain",
        tracking=True,
    )
    lead_assignment_optout = fields.Boolean(string="Pause assignment")
    lead_assignment_max = fields.Integer(
        string="Average Leads Capacity (on 30 days)",
        default=30,
    )
    lead_day_count = fields.Integer(
        string="Leads (last 24h)",
        compute="_compute_lead_day_count",
        groups="sale.group_sale_salesman,sale.group_sale_readonly",
        help="Number of leads assigned to this member in the last 24 hours, "
        "archived and lost ones included. This is what the daily assignment "
        "quota is spent against.",
    )
    lead_month_count = fields.Integer(
        string="Leads (30 days)",
        compute="_compute_lead_month_count",
        groups="sale.group_sale_salesman,sale.group_sale_readonly",
        help="Number of leads assigned to this member in the last 30 days, "
        "archived and lost ones included",
    )

    @api.depends("user_id", "team_id")
    def _compute_lead_day_count(self):
        day_date = fields.Datetime.now() - datetime.timedelta(hours=24)
        daily_leads_counts = self._get_lead_from_date(day_date)

        for member in self:
            member.lead_day_count = daily_leads_counts.get(
                (member.user_id.id, member.team_id.id), 0
            )

    @api.depends("user_id", "team_id")
    def _compute_lead_month_count(self):
        month_date = fields.Datetime.now() - datetime.timedelta(days=30)
        monthly_leads_counts = self._get_lead_from_date(month_date)

        for member in self:
            member.lead_month_count = monthly_leads_counts.get(
                (member.user_id.id, member.team_id.id), 0
            )

    def _get_lead_from_date(self, date_from, active_test=False):
        return {
            (user.id, team.id): count
            for user, team, count in self.env["crm.lead"]
            .with_context(active_test=active_test)
            ._read_group(
                [
                    ("date_open", ">=", date_from),
                    ("team_id", "in", self.team_id.ids),
                    ("user_id", "in", self.user_id.ids),
                ],
                ["user_id", "team_id"],
                ["__count"],
            )
        }

    @api.constrains("lead_assignment_domain")
    def _constrains_assignment_domain(self):
        for member in self:
            try:
                domain = literal_eval(member.lead_assignment_domain or "[]")
                if domain:
                    self.env["crm.lead"].search(domain, limit=1)  # noqa: E8507 - validates each member's own domain
            except Exception:
                raise exceptions.ValidationError(
                    _(
                        "Member assignment domain for user %(user)s and team %(team)s is incorrectly formatted",
                        user=member.user_id.name,
                        team=member.team_id.name,
                    )
                )

    @api.constrains("lead_assignment_domain_preferred")
    def _constrains_assignment_domain_preferred(self):
        for member in self:
            try:
                domain = literal_eval(member.lead_assignment_domain_preferred or "[]")
                if domain:
                    self.env["crm.lead"].search(domain, limit=1)  # noqa: E8507 - validates each member's own domain
            except Exception:
                raise exceptions.ValidationError(
                    _(
                        "Member preferred assignment domain for user %(user)s and team %(team)s is incorrectly formatted",
                        user=member.user_id.name,
                        team=member.team_id.name,
                    )
                )

    def _get_assignment_quota(self, force_quota=False):
        quota = float_round(
            self.lead_assignment_max / 30.0,
            precision_digits=0,
            rounding_method="HALF-UP",
        )
        if force_quota:
            return quota
        return quota - self.lead_day_count
