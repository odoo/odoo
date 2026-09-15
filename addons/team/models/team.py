from dataclasses import dataclass

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import TransactionMemo
from odoo.tools.misc import str2bool

_debug = DebugLog(__name__)

TEAM_SEARCHES = TransactionMemo(
    "team.team.searches", invalidated_by=("team.team", "team.member", "res.users")
)


@dataclass(frozen=True, slots=True)
class TeamUsage:
    key: str
    flag: str
    label: object
    manager_group: str
    alias_model: str | None = None
    membership_multi_param: str | None = None


class Team(models.Model):
    _name = "team.team"
    _inherit = ["mixin.mail.thread", "mixin.user.favorite", "mixin.color"]
    _description = "Team"
    _order = "sequence ASC, create_date DESC, id DESC"
    _check_company_auto = True

    def _default_favorite_user_ids(self):
        return [Command.link(self.env.uid)]

    name = fields.Char(
        string="Team",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(
        default=True,
        help="If the active field is set to false, it will allow you to hide the team without removing it.",
    )
    description = fields.Html(
        string="About Team",
        translate=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Team Leader",
        domain=[("share", "!=", True)],
        check_company=True,
    )
    color = fields.Integer(
        string="Color Index",
        default=lambda self: self._default_color(),
    )
    favorite_user_ids = fields.Many2many(
        string="Favorite Members",
        default=_default_favorite_user_ids,
    )
    is_user_favorite = fields.Boolean(
        string="Show on dashboard",
        help="Favorite teams to display them in the dashboard and access them easily.",
    )
    usage_names = fields.Char(
        string="Used In",
        compute="_compute_usage_names",
    )
    is_membership_multi = fields.Boolean(
        string="Multiple Memberships Allowed",
        compute="_compute_is_membership_multi",
        help="If True, members may belong to other teams of the same usage. Otherwise membership is limited to a single team per usage.",
    )
    can_activate_multi_membership = fields.Boolean(
        compute="_compute_can_activate_multi_membership"
    )
    member_ids = fields.Many2many(
        comodel_name="res.users",
        string="Members",
        compute="_compute_member_ids",
        inverse="_inverse_member_ids",
        search="_search_member_ids",
        domain="['&', ('share', '=', False), ('company_ids', 'in', member_company_ids)]",
        help="Users assigned to this team.",
    )
    member_company_ids = fields.Many2many(
        comodel_name="res.company",
        compute="_compute_member_company_ids",
        help="UX: Limit to team company or all if no company",
    )
    member_warning = fields.Text(
        string="Membership Issue Warning",
        compute="_compute_member_warning",
    )
    team_member_ids = fields.One2many(
        comodel_name="team.member",
        inverse_name="team_id",
        string="Team Members",
        context={"active_test": True},
        help="Add members to automatically assign their documents to this team.",
    )
    team_member_all_ids = fields.One2many(
        comodel_name="team.member",
        inverse_name="team_id",
        string="Team Members (incl. inactive)",
        context={"active_test": False},
    )
    alias_ids = fields.One2many(
        comodel_name="team.alias",
        inverse_name="team_id",
        string="Email Aliases",
    )

    @api.constrains("company_id")
    def _constrains_company_members(self):
        self.team_member_ids._check_company_membership()

    @api.model_create_multi
    def create(self, vals_list):
        alias_fields = self._get_usage_alias_related_fields()
        alias_vals_list = [
            {fname: vals.pop(fname) for fname in list(vals) if fname in alias_fields}
            for vals in vals_list
        ]
        teams = super(Team, self.with_context(mail_create_nosubscribe=True)).create(
            vals_list
        )
        for team in teams:
            team._check_usage_rights(team._get_team_usage_keys())
        # favorite_user_ids is written after the memberships created inline, and
        # replaces the favorites those memberships granted
        teams.team_member_ids._add_to_team_favorites()
        teams._sync_usage_aliases()
        # an alias field reaches its team.alias row, which exists only now
        for team, alias_vals in zip(teams, alias_vals_list, strict=True):
            if alias_vals:
                team.write(alias_vals)
        return teams

    def write(self, vals):
        flags = set(vals) & self._get_usage_flags()
        if flags:
            usages = self._get_usages()
            self._check_usage_rights(
                [
                    key
                    for key, usage in usages.items()
                    if usage.flag in flags
                    and any(team[usage.flag] != bool(vals[usage.flag]) for team in self)
                ]
            )
        res = super().write(vals)
        if "active" in vals and not vals["active"]:
            _debug.logic(
                "team_archive_cascade",
                teams=self,
                memberships=self.team_member_ids,
            )
            self.team_member_ids.action_archive()
        if flags:
            self._sync_usage_aliases()
            # a usage the team now carries may be mono for its members
            self.team_member_ids._enforce_mono_membership()
            # record rules inline a user's teams per usage
            self.env.registry.clear_cache()
        if "company_id" in vals:
            self._refresh_usage_aliases()
        return res

    def _check_usage_rights(self, keys):
        # a rule on the flag lets a usage's administrators edit its teams, but it
        # reads the team before the write: setting or clearing another usage's
        # flag must be that usage's administrators' call
        if (
            not keys
            or self.env.su
            or self.env.user.has_group("team.group_team_manager")
        ):
            return
        usages = self._get_usages()
        refused = [
            str(usages[key].label)
            for key in keys
            if not self.env.user.has_group(usages[key].manager_group)
        ]
        if refused:
            raise AccessError(
                _(
                    "Only an administrator of %(usages)s can add or remove that usage on a team.",
                    usages=", ".join(sorted(refused)),
                )
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_foreign_usage(self):
        if self.env.su or self.env.user.has_group("team.group_team_manager"):
            return
        usages = self._get_usages()
        for team in self:
            for key in team._get_team_usage_keys():
                if not self.env.user.has_group(usages[key].manager_group):
                    raise AccessError(
                        _(
                            'Team "%(team)s" is also used in %(usage)s: only a Teams Administrator can delete it.',
                            team=team.name,
                            usage=str(usages[key].label),
                        )
                    )

    def unlink(self):
        aliases = self.alias_ids.alias_id
        res = super().unlink()
        aliases.sudo().unlink()
        return res

    @api.depends(lambda self: sorted(self._get_usage_flags()))
    def _compute_usage_names(self):
        usages = self._get_usages()
        for team in self:
            team.usage_names = ", ".join(
                str(usages[key].label) for key in team._get_team_usage_keys()
            )

    @api.depends(lambda self: sorted(self._get_usage_flags()))
    def _compute_is_membership_multi(self):
        for team in self:
            team.is_membership_multi = not team._get_mono_usage_keys()

    @api.depends("is_membership_multi")
    @api.depends_context("uid")
    def _compute_can_activate_multi_membership(self):
        usages = self._get_usages()
        for team in self:
            keys = team._get_mono_usage_keys()
            team.can_activate_multi_membership = bool(keys) and all(
                self.env.user.has_group(usages[key].manager_group) for key in keys
            )

    @api.depends("team_member_ids.active", "team_member_ids.user_id")
    def _compute_member_ids(self):
        for team in self:
            team.member_ids = team.team_member_ids.user_id

    @api.depends("is_membership_multi", "member_ids")
    def _compute_member_warning(self):
        self.member_warning = False
        teams = self.filtered(lambda team: not team.is_membership_multi)
        if not teams.member_ids:
            return

        Member = self.env["team.member"]
        teams_by_user = Member._get_live_teams_by_user(teams.member_ids)
        for team in teams:
            user_names, other_teams = [], self.browse()
            for user in team.member_ids:
                elsewhere = team._filter_sharing_mono_usage(
                    teams_by_user[user] - team._origin
                )
                if elsewhere:
                    user_names.append(user.name)
                    other_teams |= elsewhere
            if user_names:
                team.member_warning = Member._get_membership_warning(
                    user_names, other_teams
                )

    @api.depends("company_id")
    def _compute_member_company_ids(self):
        all_companies = self.env["res.company"].search([])
        for team in self:
            team.member_company_ids = team.company_id or all_companies

    def _search_member_ids(self, operator, value):
        return self.env["team.member"]._search_live_projection(
            "team_member_ids", "user_id", operator, value
        )

    def _inverse_member_ids(self):
        to_create, to_archive = [], self.env["team.member"]
        for team in self:
            memberships = team.team_member_ids
            users_current = team.member_ids

            to_create += [
                {"team_id": team.id, "user_id": user.id}
                for user in users_current - memberships.user_id
            ]
            to_archive += memberships.filtered(
                lambda m, users_current=users_current: m.user_id not in users_current
            )

        if to_create:
            self.env["team.member"].create(to_create)
        if to_archive:
            to_archive.action_archive()

    @api.model
    def _get_usages(self):
        return {}

    @api.model
    def _get_usage(self, key):
        if key not in (usages := self._get_usages()):
            raise UserError(_("Unknown team usage: %(usage)s", usage=key))
        return usages[key]

    @api.model
    def _get_usage_flags(self):
        return {usage.flag for usage in self._get_usages().values()}

    @api.model
    def _get_domain_usage(self, key):
        return Domain(self._get_usage(key).flag, "=", True)

    def _get_team_usage_keys(self):
        self.check_singleton()
        return [key for key, usage in self._get_usages().items() if self[usage.flag]]

    @api.model
    def _is_membership_multi(self, key):
        param = self._get_usage(key).membership_multi_param
        if not param:
            return True
        return str2bool(
            self.env["ir.config_parameter"].sudo().get_param(param, ""),
            default=False,
        )

    def _get_mono_usage_keys(self):
        self.check_singleton()
        return [
            key
            for key in self._get_team_usage_keys()
            if not self._is_membership_multi(key)
        ]

    def _get_domain_sharing_mono_usage(self):
        self.check_singleton()
        return Domain.OR(
            self._get_domain_usage(key) for key in self._get_mono_usage_keys()
        )

    def _filter_sharing_mono_usage(self, teams):
        keys = self._get_mono_usage_keys()
        if not keys:
            return teams.browse()
        return teams.filtered_domain(self._get_domain_sharing_mono_usage())

    def action_primary_channel_button(self):
        return False

    def action_activate_multi_membership(self, flags=None):
        usages = self._get_usages()
        if flags:
            # the form sends its unsaved flags, which decide what the banner warned of
            keys = {
                key
                for key, usage in usages.items()
                if usage.membership_multi_param
                and flags.get(usage.flag)
                and not self._is_membership_multi(key)
            }
        elif self:
            keys = {key for team in self for key in team._get_mono_usage_keys()}
        else:
            keys = {
                key
                for key, usage in usages.items()
                if usage.membership_multi_param and not self._is_membership_multi(key)
            }
        refused = [
            str(usages[key].label)
            for key in keys
            if not self.env.user.has_group(usages[key].manager_group)
        ]
        if refused:
            raise AccessError(
                _(
                    "Only an administrator of %(usages)s can allow multiple team memberships there.",
                    usages=", ".join(sorted(refused)),
                )
            )
        for key in keys:
            self.env["ir.config_parameter"].sudo().set_param(
                usages[key].membership_multi_param, True
            )

    def _get_default_team(self, usage, user_id=False, domain=(), fallback=True):
        user = (
            self.env["res.users"].sudo().browse(user_id) if user_id else self.env.user
        )
        live = self._get_domain_live_team(user, usage)
        own_teams = self._search_ignoring_access(
            live
            & (Domain("user_id", "=", user.id) | Domain("member_ids", "in", user.ids))
        )
        context_team = self._get_context_default_team(live)
        preferred = own_teams.filtered_domain(domain) if domain else own_teams

        if candidates := preferred or own_teams:
            team = context_team if context_team in candidates else candidates[:1]
            _debug.logic(
                "default_team_own",
                usage=usage,
                user=user,
                context_team=context_team,
                preferred=bool(preferred),
                team=team,
            )
            return team

        team = context_team
        if not team and domain and fallback:
            team = self._search_ignoring_access(live & Domain(domain), limit=1)
        if not team and fallback:
            team = self._search_ignoring_access(live, limit=1)
        _debug.logic(
            "default_team_fallback",
            usage=usage,
            user=user,
            context_team=context_team,
            domain=domain,
            team=team,
        )
        return team

    def _get_context_default_team(self, live_domain):
        if context_team_id := self.env.context.get("default_team_id"):
            return self._search_ignoring_access(
                live_domain & Domain("id", "=", context_team_id)
            )
        return self.browse()

    @api.model
    def _drop_default_of_other_usage(self, defaults, usage, field_name="team_id"):
        if team_id := defaults.get(field_name):
            team = self.sudo().browse(team_id).exists()
            if not team.filtered_domain(self._get_domain_usage(usage)):
                del defaults[field_name]
        return defaults

    def _get_domain_live_team(self, user, usage):
        company_ids = (user.company_ids & self.env.companies).ids
        return (
            Domain("active", "=", True)
            & Domain("company_id", "in", [False, *company_ids])
            & self._get_domain_usage(usage)
        )

    def _search_ignoring_access(self, domain, limit=None):
        memo = TEAM_SEARCHES(self.env)
        key = (Domain(domain), limit)
        if key not in memo:
            memo[key] = self.sudo().search(domain, limit=limit).ids
        return self.browse(memo[key])

    def _get_usage_alias(self, key):
        self.check_singleton()
        return self.alias_ids.filtered(lambda alias: alias.usage == key)

    def _notify_get_usage_reply_to_addresses(self, key):
        addresses = {}
        for team in self:
            alias = team._get_usage_alias(key)
            if alias.alias_name and alias.alias_domain_id:
                addresses[team.id] = alias.alias_full_name
        leftover = self.filtered(lambda team: team.id not in addresses)
        for company, teams in leftover.grouped(
            lambda team: team.company_id or self.env.company
        ).items():
            if company.catchall_email:
                addresses.update(dict.fromkeys(teams.ids, company.catchall_email))
        return addresses

    @api.model
    def _get_usage_alias_related_fields(self):
        alias_fields = {
            name
            for name, field in self._fields.items()
            if field.type == "many2one" and field.comodel_name == "team.alias"
        }
        return {
            name
            for name, field in self._fields.items()
            if field.related and field.related.split(".", 1)[0] in alias_fields
        }

    def _compute_usage_alias_field(self, key, field_name):
        for team in self:
            team[field_name] = team.alias_ids.filtered(
                lambda alias, key=key: alias.usage == key
            )[:1]

    @api.model
    def _search_usage_alias_field(self, key, operator, value):
        of_usage = Domain("usage", "=", key)
        if operator in ("any", "any!"):
            return Domain("alias_ids", operator, of_usage & Domain(value))
        if operator in ("not any", "not any!"):
            return ~Domain("alias_ids", operator[4:], of_usage & Domain(value))
        if operator == "in":
            ids = [alias_id for alias_id in value if alias_id]
            some = (
                Domain("alias_ids", "any", of_usage & Domain("id", "in", ids))
                if ids
                else Domain.FALSE
            )
            none = (
                ~Domain("alias_ids", "any", of_usage)
                if False in value
                else Domain.FALSE
            )
            return some | none
        return NotImplemented

    def _prepare_usage_alias_defaults(self, key):
        self.check_singleton()
        return {"team_id": self.id}

    def _prepare_usage_alias_vals(self, key):
        self.check_singleton()
        IrModel = self.env["ir.model"]
        return {
            "alias_model_id": IrModel._get_id(self._get_usage(key).alias_model),
            "alias_parent_model_id": IrModel._get_id(self._name),
            "alias_parent_thread_id": self.id,
            "alias_defaults": str(self._prepare_usage_alias_defaults(key)),
            "alias_domain_id": (
                self.company_id.alias_domain_id or self.env.company.alias_domain_id
            ).id,
        }

    def _refresh_usage_aliases(self, keys=None):
        aliases = self.alias_ids
        if keys is not None:
            aliases = aliases.filtered(lambda alias: alias.usage in keys)
        aliases._refresh_alias_values()

    @api.model
    def _sync_all_usage_aliases(self):
        self.with_context(active_test=False).search([])._sync_usage_aliases()

    def _sync_usage_aliases(self):
        usages = {
            key: usage for key, usage in self._get_usages().items() if usage.alias_model
        }
        if not usages:
            return
        to_create, to_remove = [], self.env["team.alias"]
        for team in self:
            existing = {alias.usage: alias for alias in team.alias_ids}
            for key, usage in usages.items():
                if team[usage.flag] and key not in existing:
                    to_create.append({"team_id": team.id, "usage": key})
                elif not team[usage.flag] and key in existing:
                    to_remove |= existing[key]
        _debug.lifecycle(
            "usage_aliases_synced",
            teams=self,
            created=len(to_create),
            removed=to_remove,
        )
        if to_remove:
            to_remove.sudo().unlink()
        if to_create:
            self.env["team.alias"].sudo().create(to_create)
