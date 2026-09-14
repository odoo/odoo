from odoo import Command, _, api, exceptions, fields, models
from odoo.fields import NEGATIVE_CONDITION_OPERATORS, Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class CrmTeamMember(models.Model):
    _name = "crm.team.member"
    _inherit = ["mixin.mail.thread"]
    _description = "Sales Team Member"
    _rec_name = "user_id"
    _order = "create_date ASC, id"

    crm_team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        index=True,
        required=True,
        group_expand="_read_group_expand_full",
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        index=True,
        required=True,
        domain="""[
            ('share', '=', False),
            ('crm_team_member_ids', 'not any', [('active', '=', True), ('crm_team_id', '=', crm_team_id), ('id', '!=', id)]),
            ('company_ids', 'in', user_company_ids),
        ]""",
        ondelete="cascade",
    )
    user_company_ids = fields.Many2many(
        comodel_name="res.company",
        compute="_compute_user_company_ids",
        help="UX: Limit to team company or all if no company",
    )
    active = fields.Boolean(default=True)
    member_warning = fields.Text(compute="_compute_member_warning")
    image_1920 = fields.Image(
        related="user_id.image_1920",
        string="Image",
    )
    image_128 = fields.Image(
        related="user_id.image_128",
        string="Image (128)",
    )
    name = fields.Char(
        related="user_id.display_name",
        string="Name",
    )
    email = fields.Char(
        related="user_id.email",
        string="Email",
    )
    phone_ids = fields.Many2many(
        related="user_id.phone_ids",
        string="Phone Numbers",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="user_id.company_id",
        string="Company",
    )

    @api.constrains("crm_team_id", "user_id", "active")
    def _constrains_membership(self):
        active = self.filtered("active")
        if not active:
            return
        existing = self.sudo().search(
            [
                ("crm_team_id", "in", active.crm_team_id.ids),
                ("user_id", "in", active.user_id.ids),
                ("active", "=", True),
            ]
        )
        touched = {(member.crm_team_id.id, member.user_id.id) for member in active}
        seen, duplicates = set(), self.browse()
        for membership in existing:
            key = (membership.crm_team_id.id, membership.user_id.id)
            if key not in touched:
                continue
            if key in seen:
                duplicates |= membership
            seen.add(key)

        if duplicates:
            raise exceptions.ValidationError(
                _(
                    "You are trying to create duplicate membership(s). We found that %(duplicates)s already exist(s).",
                    duplicates=", ".join(
                        "%s (%s)" % (m.user_id.name, m.crm_team_id.name)
                        for m in duplicates
                    ),
                )
            )

    @api.constrains("crm_team_id", "user_id", "active")
    def _constrains_company_membership(self):
        self._check_company_membership()

    @api.constrains("crm_team_id", "user_id", "active")
    def _constrains_live_endpoints(self):
        for membership in self.filtered("active"):
            if not membership.crm_team_id.active:
                raise exceptions.ValidationError(
                    _(
                        "Sales Team '%(team)s' is archived and cannot take new members.",
                        team=membership.crm_team_id.name,
                    )
                )
            if not membership.user_id.active:
                raise exceptions.ValidationError(
                    _(
                        "Salesperson '%(user)s' is archived and cannot join a sales team.",
                        user=membership.user_id.name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        memberships = super(
            CrmTeamMember, self.with_context(mail_create_nosubscribe=True)
        ).create(vals_list)
        memberships._on_membership_changed()
        return memberships

    def write(self, vals):
        res = super().write(vals)
        if vals.keys() & {"active", "user_id", "crm_team_id"}:
            self._on_membership_changed()
        return res

    def unlink(self):
        res = super().unlink()
        self._clear_membership_dependent_caches()
        return res

    @api.depends("crm_team_id", "crm_team_id.company_id")
    def _compute_user_company_ids(self):
        all_companies = self.env["res.company"].search([])
        for member in self:
            member.user_company_ids = member.crm_team_id.company_id or all_companies

    @api.depends("active", "user_id", "crm_team_id")
    def _compute_member_warning(self):
        if self.env["crm.team"]._is_membership_multi():
            self.member_warning = False
            return

        active = self.filtered("active")
        (self - active).member_warning = False
        if not active:
            return

        teams_by_user = self._get_live_teams_by_user(active.user_id)
        for member in active:
            remaining = teams_by_user.get(member.user_id, self.env["crm.team"]) - (
                member.crm_team_id | member._origin.crm_team_id
            )
            if remaining:
                member.member_warning = self._get_membership_warning(
                    [member.user_id.name], remaining
                )
            else:
                member.member_warning = False

    @api.model
    def _search_live_projection(self, membership_field, target_field, operator, value):
        if operator in NEGATIVE_CONDITION_OPERATORS:
            return NotImplemented

        live = Domain("active", "=", True)
        if operator != "in":
            return Domain(
                membership_field, "any!", live & Domain(target_field, operator, value)
            )

        targets = [target for target in value if target]
        some = (
            Domain(membership_field, "any!", live & Domain(target_field, "in", targets))
            if targets
            else Domain.FALSE
        )
        empty = (
            Domain(membership_field, "not any!", live)
            if False in value
            else Domain.FALSE
        )
        return empty | some

    @api.model
    def _get_live_teams_by_user(self, users):
        teams_by_user = dict.fromkeys(users, self.env["crm.team"])
        if not users.ids:
            return teams_by_user
        for membership in self.search(
            [("active", "=", True), ("user_id", "in", users.ids)]
        ):
            teams_by_user[membership.user_id] |= membership.crm_team_id
        return teams_by_user

    @api.model
    def _get_membership_warning(self, user_names, teams):
        return _(
            "%(user_names)s already in other teams (%(team_names)s).",
            user_names=", ".join(user_names),
            team_names=", ".join(teams.mapped("name")),
        )

    def _check_company_membership(self):
        foreign = self.filtered(
            lambda m: (
                m.active
                and m.crm_team_id.company_id
                and m.crm_team_id.company_id not in m.user_id.company_ids
            )
        )
        if not foreign:
            return
        team = foreign.crm_team_id[:1]
        raise exceptions.ValidationError(
            _(
                "The following team members are not allowed in company '%(company)s' of the Sales Team '%(team)s': %(users)s",
                company=team.company_id.display_name,
                team=team.name,
                users=", ".join(
                    foreign.filtered(lambda m: m.crm_team_id == team).user_id.mapped(
                        "name"
                    )
                ),
            )
        )

    def _on_membership_changed(self):
        self._enforce_mono_membership()
        self._add_to_team_favorites()
        self._clear_membership_dependent_caches()

    def _add_to_team_favorites(self):
        for team, memberships in self.filtered("active").grouped("crm_team_id").items():
            team.favorite_user_ids = [
                Command.link(user_id) for user_id in memberships.user_id.ids
            ]

    def _enforce_mono_membership(self):
        if self.env["crm.team"]._is_membership_multi():
            return
        winners = {member.user_id.id: member for member in self.filtered("active")}
        if not winners:
            return

        obsolete = (
            self.sudo()
            .search(
                [
                    ("active", "=", True),
                    ("user_id", "in", list(winners)),
                    ("id", "not in", [member.id for member in winners.values()]),
                ]
            )
            .filtered(lambda m: m.crm_team_id != winners[m.user_id.id].crm_team_id)
        )
        if obsolete:
            _debug.logic("mono_membership_evicted", winners=self, evicted=obsolete)
            obsolete.action_archive()

    def _clear_membership_dependent_caches(self):
        _debug.logic("membership_caches_cleared", memberships=self)
        self.env.registry.clear_cache()
