import datetime
import logging
import random
from ast import literal_eval

from markupsafe import Markup

from odoo import _, api, exceptions, fields, models, modules
from odoo.fields import Domain
from odoo.tools import float_compare, float_round
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ["mixin.mail.alias", "crm.team"]
    _description = "Sales Team"

    use_leads = fields.Boolean(
        string="Leads",
        help="Check this box to filter and qualify incoming requests as leads before converting them into opportunities and assigning them to a salesperson.",
    )
    use_opportunities = fields.Boolean(
        string="Pipeline",
        help="Check this box to manage a presales process with opportunities.",
        default=True,
    )
    alias_id = fields.Many2one(
        help="The email address associated with this channel. New emails received will automatically create new leads assigned to the channel."
    )
    assignment_enabled = fields.Boolean(
        string="Lead Assign",
        compute="_compute_assignment_enabled",
    )
    assignment_auto_enabled = fields.Boolean(
        string="Auto Assignment",
        compute="_compute_assignment_enabled",
    )
    assignment_optout = fields.Boolean(string="Skip auto assignment")
    assignment_max = fields.Integer(
        string="Lead Average Capacity",
        help="Monthly average leads capacity for all salesmen belonging to the team",
        compute="_compute_assignment_max",
    )
    assignment_domain = fields.Char(
        help="Additional filter domain when fetching unassigned leads to allocate to the team.",
        tracking=True,
    )
    lead_unassigned_count = fields.Integer(
        string="# Unassigned Leads",
        compute="_compute_lead_unassigned_count",
    )
    lead_all_assigned_month_count = fields.Integer(
        string="# Leads/Opps assigned this month",
        help="Number of leads and opportunities assigned this last month.",
        compute="_compute_lead_all_assigned_month_count",
    )
    lead_all_assigned_month_exceeded = fields.Boolean(
        string="Exceed monthly lead assignement",
        help="True if the monthly lead assignment count is greater than the maximum assignment limit, false otherwise.",
        compute="_compute_lead_all_assigned_month_count",
    )
    lead_properties_definition = fields.PropertiesDefinition(string="Lead Properties")

    # `crm_team_member_ids` is active-filtered and archiving a team archives its
    # members, so the set itself changes on a write nothing here declared: a
    # team archived with one member kept `assignment_max` at that member's value
    # while the database read 0.
    @api.depends("crm_team_member_ids.assignment_max", "crm_team_member_ids.active")
    def _compute_assignment_max(self):
        for team in self:
            team.assignment_max = sum(
                member.assignment_max for member in team.crm_team_member_ids
            )

    def _compute_assignment_enabled(self):
        assign_enabled = self.env["crm.lead"]._is_rule_based_assignment_activated()
        auto_assign_enabled = False
        if assign_enabled:
            assign_cron = self.sudo().env.ref(
                "crm.ir_cron_crm_lead_assign", raise_if_not_found=False
            )
            auto_assign_enabled = assign_cron.active if assign_cron else False
        self.assignment_enabled = assign_enabled
        self.assignment_auto_enabled = auto_assign_enabled

    def _compute_lead_unassigned_count(self):
        leads_data = self.env["crm.lead"]._read_group(
            [
                ("team_id", "in", self.ids),
                ("user_id", "=", False),
            ],
            ["team_id"],
            ["__count"],
        )
        counts = {team.id: count for team, count in leads_data}
        for team in self:
            team.lead_unassigned_count = counts.get(team.id, 0)

    @api.depends("crm_team_member_ids.lead_month_count", "assignment_max")
    def _compute_lead_all_assigned_month_count(self):
        for team in self:
            team.lead_all_assigned_month_count = sum(
                member.lead_month_count for member in team.crm_team_member_ids
            )
            team.lead_all_assigned_month_exceeded = (
                team.lead_all_assigned_month_count > team.assignment_max
            )

    @api.onchange("use_leads", "use_opportunities")
    def _onchange_use_leads_opportunities(self):
        if not self.use_leads and not self.use_opportunities:
            self.alias_name = False

    @api.constrains("assignment_domain")
    def _constrains_assignment_domain(self):
        for team in self:
            try:
                domain = literal_eval(team.assignment_domain or "[]")
                if domain:
                    self.env["crm.lead"].search(domain, limit=1)  # noqa: E8507 - validates each team's own domain
            except Exception:
                raise exceptions.ValidationError(
                    _(
                        "Assignment domain for team %(team)s is incorrectly formatted",
                        team=team.name,
                    )
                )

    def write(self, vals):
        result = super().write(vals)
        if "use_leads" in vals or "use_opportunities" in vals:
            for team in self:
                alias_vals = team._alias_get_creation_values()
                team.write(
                    {
                        "alias_name": alias_vals.get("alias_name", team.alias_name),
                        "alias_defaults": alias_vals.get("alias_defaults"),
                    }
                )
        return result

    def unlink(self):
        frequencies = self.env["crm.lead.scoring.frequency"].search(
            [("team_id", "in", self.ids)]
        )
        if frequencies:
            existing_noteam = (
                self.env["crm.lead.scoring.frequency"]
                .sudo()
                .search(
                    [
                        ("team_id", "=", False),
                        ("variable", "in", frequencies.mapped("variable")),
                    ]
                )
            )
            for frequency in frequencies:
                if (
                    float_compare(frequency.won_count, 0.1, 2) != 1
                    and float_compare(frequency.lost_count, 0.1, 2) != 1
                ):
                    continue

                match = existing_noteam.filtered(
                    lambda frequ_nt: (
                        frequ_nt.variable == frequency.variable
                        and frequ_nt.value == frequency.value
                    )
                )
                if match:
                    exist_won_count = float_round(
                        match.won_count, precision_digits=0, rounding_method="HALF-UP"
                    )
                    exist_lost_count = float_round(
                        match.lost_count, precision_digits=0, rounding_method="HALF-UP"
                    )
                    add_won_count = float_round(
                        frequency.won_count,
                        precision_digits=0,
                        rounding_method="HALF-UP",
                    )
                    add_lost_count = float_round(
                        frequency.lost_count,
                        precision_digits=0,
                        rounding_method="HALF-UP",
                    )
                    new_won_count = exist_won_count + add_won_count
                    new_lost_count = exist_lost_count + add_lost_count
                    match.won_count = (
                        new_won_count
                        if float_compare(new_won_count, 0.1, 2) == 1
                        else 0.1
                    )
                    match.lost_count = (
                        new_lost_count
                        if float_compare(new_lost_count, 0.1, 2) == 1
                        else 0.1
                    )
                else:
                    existing_noteam += (
                        self.env["crm.lead.scoring.frequency"]
                        .sudo()
                        .create(
                            {
                                "lost_count": frequency.lost_count
                                if float_compare(frequency.lost_count, 0.1, 2) == 1
                                else 0.1,
                                "team_id": False,
                                "value": frequency.value,
                                "variable": frequency.variable,
                                "won_count": frequency.won_count
                                if float_compare(frequency.won_count, 0.1, 2) == 1
                                else 0.1,
                            }
                        )
                    )
        return super().unlink()

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get("crm.lead").id
        if self.id:
            if not self.use_leads and not self.use_opportunities:
                values["alias_name"] = False
            values["alias_defaults"] = defaults = self._get_alias_defaults()
            has_group_use_lead = self.env.user.has_group("crm.group_use_lead")
            defaults["type"] = (
                "lead" if has_group_use_lead and self.use_leads else "opportunity"
            )
            defaults["team_id"] = self.id
        return values

    @api.model
    def _get_team_for_user(self, user, current_team=None, domain=None):
        if not user:
            return self.browse()
        if current_team and user in (current_team.member_ids | current_team.user_id):
            return current_team
        return self._get_default_team_id(user_id=user.id, domain=domain or ())

    @api.model
    def _cron_assign_leads(self, force_quota=False, creation_delta_days=7):
        self.env["crm.team"].search(
            [
                "&",
                "|",
                ("use_leads", "=", True),
                ("use_opportunities", "=", True),
                ("assignment_optout", "=", False),
            ]
        )._action_assign_leads(
            force_quota=force_quota, creation_delta_days=creation_delta_days
        )
        return True

    def action_assign_leads(self):
        teams_data, members_data = self._action_assign_leads(
            force_quota=True, creation_delta_days=0
        )

        logs = self._action_assign_leads_logs(teams_data, members_data)
        html_message = Markup("<br />").join(logs)
        notif_message = " ".join(logs)

        log_action = _(
            "Lead Assignment requested by %(user_name)s", user_name=self.env.user.name
        )
        log_message = Markup("<p>%s<br /><br />%s</p>") % (log_action, html_message)
        self._message_log_batch(bodies=dict((team.id, log_message) for team in self))

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Leads Assigned"),
                "message": notif_message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _action_assign_leads(self, force_quota=False, creation_delta_days=7):
        if not (
            self.env.user.has_group("sales_team.group_sale_manager")
            or self.env.is_system()
        ):
            raise exceptions.UserError(
                _(
                    "Lead/Opportunities automatic assignment is limited to managers or administrators"
                )
            )

        _logger.info(
            "### START Lead Assignment (%d teams, %d sales persons, force daily quota: %s)",
            len(self),
            len(self.crm_team_member_ids),
            "ON" if force_quota else "OFF",
        )
        teams_data = self._allocate_leads(creation_delta_days=creation_delta_days)
        _logger.info("### Team repartition done. Starting salesmen assignment.")
        members_data = self._update_members_with_leads(force_quota=force_quota)
        _logger.info("### END Lead Assignment")
        return teams_data, members_data

    def _action_assign_leads_logs(self, teams_data, members_data):
        assigned = sum(
            len(teams_data[team]["assigned"]) + len(teams_data[team]["merged"])
            for team in teams_data
        )
        duplicates = sum(len(teams_data[team]["duplicates"]) for team in teams_data)
        members = len(members_data)
        members_assigned = sum(
            len(member_data["assigned"]) for member_data in members_data.values()
        )

        message_parts = []
        if duplicates:
            message_parts.append(
                _(
                    "%(duplicates)s duplicates leads have been merged.",
                    duplicates=duplicates,
                )
            )

        if not assigned and not members_assigned:
            if len(self) == 1:
                if not self.assignment_max:
                    message_parts.append(
                        _(
                            "No allocated leads to %(team_name)s team because it has no capacity. Add capacity to its salespersons.",
                            team_name=self.name,
                        )
                    )
                else:
                    message_parts.append(
                        _(
                            "No allocated leads to %(team_name)s team and its salespersons because no unassigned lead matches its domain.",
                            team_name=self.name,
                        )
                    )
            else:
                message_parts.append(
                    _(
                        "No allocated leads to any team or salesperson. Check your Sales Teams and Salespersons configuration as well as unassigned leads."
                    )
                )

        if not assigned and members_assigned:
            if len(self) == 1:
                message_parts.append(
                    _(
                        "No new lead allocated to %(team_name)s team because no unassigned lead matches its domain.",
                        team_name=self.name,
                    )
                )
            else:
                message_parts.append(
                    _(
                        "No new lead allocated to the teams because no lead match their domains."
                    )
                )
        elif assigned:
            if len(self) == 1:
                message_parts.append(
                    _(
                        "%(assigned)s leads allocated to %(team_name)s team.",
                        assigned=assigned,
                        team_name=self.name,
                    )
                )
            else:
                message_parts.append(
                    _(
                        "%(assigned)s leads allocated among %(team_count)s teams.",
                        assigned=assigned,
                        team_count=len(self),
                    )
                )

        if not members_assigned and assigned:
            message_parts.append(
                _(
                    "No lead assigned to salespersons because no unassigned lead matches their domains."
                )
            )
        elif members_assigned:
            message_parts.append(
                _(
                    "%(members_assigned)s leads assigned among %(member_count)s salespersons.",
                    members_assigned=members_assigned,
                    member_count=members,
                )
            )

        return message_parts

    def _allocate_leads(self, creation_delta_days=7):
        BUNDLE_HOURS_DELAY = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("crm.assignment.delay", default=0)
        )
        BUNDLE_COMMIT_SIZE = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("crm.assignment.commit.bundle", 100)
        )
        auto_commit = not modules.module.current_test

        max_create_dt = self.env.cr.now() - datetime.timedelta(hours=BUNDLE_HOURS_DELAY)
        duplicates_lead_cache = dict()

        teams_data, population, weights = dict(), list(), list()
        for team in self:
            if not team.assignment_max:
                continue

            lead_domain = Domain.AND(
                [
                    literal_eval(team.assignment_domain or "[]"),
                    [("create_date", "<=", max_create_dt)],
                    ["&", ("team_id", "=", False), ("user_id", "=", False)],
                    [("won_status", "!=", "won")],
                ]
            )
            if creation_delta_days > 0:
                lead_domain &= Domain(
                    "create_date",
                    ">",
                    self.env.cr.now() - datetime.timedelta(days=creation_delta_days),
                )

            leads = self.env["crm.lead"].search(lead_domain)  # noqa: E8507 - one query per team, on the team's own assignment domain
            missing = leads.filtered(lambda lead: lead not in duplicates_lead_cache)
            if missing:
                duplicates_lead_cache.update(
                    self.env["crm.lead"]._get_lead_duplicates_by_lead(missing)
                )

            teams_data[team] = {
                "team": team,
                "leads": leads,
                "assigned": set(),
                "merged": set(),
                "duplicates": set(),
            }
            population.append(team)
            weights.append(team.assignment_max)

        if auto_commit:
            self.env.cr.commit()

        global_data = dict(assigned=set(), merged=set(), duplicates=set())
        leads_done_ids, lead_unlink_ids, counter = set(), set(), 0
        while population:
            counter += 1
            team = random.choices(population, weights=weights, k=1)[0]

            teams_data[team]["leads"] = teams_data[team]["leads"].filtered(
                lambda l: l.id not in leads_done_ids
            )
            if not teams_data[team]["leads"]:
                population_index = population.index(team)
                population.pop(population_index)
                weights.pop(population_index)
                continue

            candidate_lead = teams_data[team]["leads"][0]
            assign_res = team._allocate_leads_deduplicate(
                candidate_lead, duplicates_cache=duplicates_lead_cache
            )
            for key in ("assigned", "merged", "duplicates"):
                teams_data[team][key].update(assign_res[key])
                leads_done_ids.update(assign_res[key])
                global_data[key].update(assign_res[key])
            lead_unlink_ids.update(assign_res["duplicates"])

            if auto_commit and counter % BUNDLE_COMMIT_SIZE == 0:
                self.env["crm.lead"].browse(lead_unlink_ids).unlink()
                lead_unlink_ids = set()
                self.env.cr.commit()

        self.env["crm.lead"].browse(lead_unlink_ids).unlink()

        if auto_commit:
            self.env.cr.commit()

        _logger.info(
            "## Assigned %s leads",
            (len(global_data["assigned"]) + len(global_data["merged"])),
        )
        for team, team_data in teams_data.items():
            _logger.info(
                "## Assigned %s leads to team %s",
                len(team_data["assigned"]) + len(team_data["merged"]),
                team.id,
            )
            _logger.info(
                "\tLeads: direct assign %s / merge result %s / duplicates merged: %s",
                team_data["assigned"],
                team_data["merged"],
                team_data["duplicates"],
            )
        return teams_data

    def _allocate_leads_deduplicate(self, leads, duplicates_cache=None):
        self.check_singleton()
        duplicates_cache = duplicates_cache if duplicates_cache is not None else dict()

        leads_assigned = self.env["crm.lead"]
        leads_done_ids, leads_merged_ids, leads_dup_ids = set(), set(), set()
        leads_dups_dict = dict()
        missing = leads.filtered(lambda lead: lead not in duplicates_cache)
        if missing:
            duplicates_cache.update(
                self.env["crm.lead"]._get_lead_duplicates_by_lead(missing)
            )

        for lead in leads:
            if lead.id not in leads_done_ids:
                lead_duplicates = duplicates_cache[lead].exists()

                if len(lead_duplicates) > 1:
                    leads_dups_dict[lead] = lead_duplicates
                    leads_done_ids.update((lead + lead_duplicates).ids)
                else:
                    leads_assigned += lead
                    leads_done_ids.add(lead.id)

        dups_to_assign = [lead for lead in leads_dups_dict]
        leads_assigned.union(*dups_to_assign)._handle_salesmen_assignment(
            user_ids=None, team_id=self.id
        )

        for lead in leads.filtered(lambda lead: lead in leads_dups_dict):
            lead_duplicates = leads_dups_dict[lead]
            merged = lead_duplicates._merge_opportunity(
                user_id=False, team_id=False, auto_unlink=False, max_length=0
            )
            leads_dup_ids.update((lead_duplicates - merged).ids)
            leads_merged_ids.add(merged.id)

        return {
            "assigned": set(leads_assigned.ids),
            "merged": leads_merged_ids,
            "duplicates": leads_dup_ids,
        }

    def _get_domain_lead_to_assign(self):
        return [
            ("user_id", "=", False),
            ("date_open", "=", False),
            ("team_id", "in", self.ids),
        ]

    def _update_members_with_leads(self, force_quota=False):
        auto_commit = not modules.module.current_test
        result_data = {}
        commit_bundle_size = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("crm.assignment.commit.bundle", 100)
        )
        teams_with_members = self.filtered(lambda team: team.crm_team_member_ids)
        quota_per_member = {
            member: member._get_assignment_quota(force_quota=force_quota)
            for member in self.crm_team_member_ids
        }
        counter = 0
        leads_per_team = dict(
            self.env["crm.lead"]._read_group(
                teams_with_members._get_domain_lead_to_assign(),
                ["team_id"],
                ["id:array_agg"],
            )
        )

        def update_lead_assignment(
            lead, members, member_leads, members_quota, assign_lst, optional_lst=None
        ):
            member_found = next(
                (member for member in members if lead in member_leads[member]), False
            )
            if not member_found:
                return None
            lead.with_context(mail_auto_subscribe_no_notify=True).convert_opportunity(
                lead.partner_id, user_ids=member_found.user_id.ids
            )
            result_data[member_found]["assigned"] += lead

            assign_lst.remove(member_found)
            if optional_lst is not None:
                optional_lst.remove(member_found)
            members_quota[member_found] -= 1
            if members_quota[member_found] > 0:
                assign_lst.append(member_found)
                if optional_lst is not None:
                    optional_lst.append(member_found)
            return member_found

        for team, leads_to_assign_ids in leads_per_team.items():
            members_to_assign = list(
                team.crm_team_member_ids.filtered(
                    lambda member: (
                        not member.assignment_optout
                        and quota_per_member.get(member, 0) > 0
                    )
                ).sorted(
                    key=lambda member: quota_per_member.get(member, 0), reverse=True
                )
            )
            if not members_to_assign:
                continue
            result_data.update(
                {
                    member: {
                        "assigned": self.env["crm.lead"],
                        "quota": quota_per_member[member],
                    }
                    for member in members_to_assign
                }
            )
            to_assign = self.env["crm.lead"].browse(leads_to_assign_ids).exists()

            members_to_assign_wpref = [
                m
                for m in members_to_assign
                if m.assignment_domain_preferred
                and literal_eval(m.assignment_domain_preferred or "")
            ]
            preferred_leads_per_member = {
                member: to_assign.filtered_domain(
                    Domain.AND(
                        [
                            literal_eval(member.assignment_domain or "[]"),
                            literal_eval(member.assignment_domain_preferred),
                        ]
                    )
                )
                for member in members_to_assign_wpref
            }
            preferred_leads = self.env["crm.lead"].concat(
                *[lead for lead in preferred_leads_per_member.values()]
            )
            assigned_preferred_leads = self.env["crm.lead"]

            for lead in preferred_leads.sorted(lambda lead: (-lead.probability, id)):
                counter += 1
                member_found = update_lead_assignment(
                    lead,
                    members_to_assign_wpref,
                    preferred_leads_per_member,
                    quota_per_member,
                    members_to_assign,
                    members_to_assign_wpref,
                )
                if not member_found:
                    continue
                assigned_preferred_leads += lead
                if auto_commit and counter % commit_bundle_size == 0:
                    self.env.cr.commit()

            to_assign = to_assign - assigned_preferred_leads
            leads_per_member = {
                member: to_assign.filtered_domain(
                    literal_eval(member.assignment_domain or "[]")
                )
                for member in members_to_assign
            }
            for lead in to_assign.sorted(lambda lead: (-lead.probability, id)):
                counter += 1
                member_found = update_lead_assignment(
                    lead,
                    members_to_assign,
                    leads_per_member,
                    quota_per_member,
                    members_to_assign,
                )
                if not member_found:
                    continue
                if auto_commit and counter % commit_bundle_size == 0:
                    self.env.cr.commit()

            if auto_commit:
                self.env.cr.commit()
            self.env.invalidate_all()
            _logger.info(
                "Team %s: Assigned %s leads based on preference, on a potential of %s (limited by quota)",
                team.name,
                len(assigned_preferred_leads),
                len(preferred_leads),
            )
        _logger.info(
            "Assigned %s leads to %s salesmen",
            sum(len(r["assigned"]) for r in result_data.values()),
            len(result_data),
        )
        for member, member_info in result_data.items():
            _logger.info(
                "-> member %s of team %s: assigned %d/%d leads (%s)",
                member.id,
                member.crm_team_id.id,
                len(member_info["assigned"]),
                member_info["quota"],
                member_info["assigned"],
            )
        return result_data

    @api.model
    def action_your_pipeline(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_lead_action_pipeline"
        )
        return self._action_update_to_pipeline(action)

    @api.model
    def action_opportunity_forecast(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_lead_action_forecast"
        )
        return self._action_update_to_pipeline(action)

    def action_view_leads(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_case_form_view_salesteams_opportunity"
        )
        rcontext = {
            "team": self,
        }
        action["help"] = self.env["ir.ui.view"]._render_template(
            "crm.crm_action_helper", values=rcontext
        )
        return action

    def action_view_unassigned_leads(self):
        action = self.action_view_leads()
        context_str = action.get("context", "{}")
        if context_str:
            try:
                context = safe_eval(
                    action["context"], {"active_id": self.id, "uid": self.env.uid}
                )
            except NameError, ValueError:
                context = {}
        else:
            context = {}
        action["context"] = context | {"search_default_unassigned": True}
        return action

    @api.model
    def _action_update_to_pipeline(self, action):
        self.check_access("read")
        user_team_id = self.env.user.sale_team_id.id
        if not user_team_id:
            user_team_id = self.search([], limit=1).id
            action["help"] = "<p class='o_view_nocontent_smiling_face'>%s</p><p>" % _(
                "Create an Opportunity"
            )
            if user_team_id:
                if self.env.user.has_group("sales_team.group_sale_manager"):
                    action["help"] += "<p>%s</p>" % _(
                        """As you are a member of no Sales Team, you are showed the Pipeline of the <b>first team by default.</b>
                                        To work with the CRM, you should <a name="%d" type="action" tabindex="-1">join a team.</a>""",
                        self.env.ref("sales_team.crm_team_action_config").id,
                    )
                else:
                    action["help"] += (
                        "<p>%s</p>"
                        % _("""As you are a member of no Sales Team, you are showed the Pipeline of the <b>first team by default.</b>
                                        To work with the CRM, you should join a team.""")
                    )
        try:
            action_context = safe_eval(action["context"], {"uid": self.env.uid})
        except NameError, ValueError:
            action_context = {}
        action["context"] = action_context
        return action

    @api.depends("use_opportunities")
    def _compute_dashboard_button_name(self):
        super()._compute_dashboard_button_name()
        team_with_pipelines = self.filtered(lambda el: el.use_opportunities)
        team_with_pipelines.update({"dashboard_button_name": _("Pipeline")})

    def action_primary_channel_button(self):
        self.check_singleton()
        if self.use_opportunities:
            return self.action_view_leads()
        return super().action_primary_channel_button()
