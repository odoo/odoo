from odoo import Command, _, api, exceptions, fields, models
from odoo.fields import NEGATIVE_CONDITION_OPERATORS, Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class TeamMember(models.Model):
    _name = "team.member"
    _inherit = ["mixin.mail.thread"]
    _description = "Team Member"
    _rec_name = "user_id"
    _order = "create_date ASC, id"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Team",
        index=True,
        required=True,
        group_expand="_read_group_expand_full",
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Member",
        index=True,
        required=True,
        domain="""[
            ('share', '=', False),
            ('team_member_ids', 'not any', [('active', '=', True), ('team_id', '=', team_id), ('id', '!=', id)]),
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
    can_activate_multi_membership = fields.Boolean(
        related="team_id.can_activate_multi_membership"
    )
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

    @api.constrains("team_id", "user_id", "active")
    def _constrains_membership(self):
        active = self.filtered("active")
        if not active:
            return
        existing = self.sudo().search(
            [
                ("team_id", "in", active.team_id.ids),
                ("user_id", "in", active.user_id.ids),
                ("active", "=", True),
            ]
        )
        touched = {(member.team_id.id, member.user_id.id) for member in active}
        seen, duplicates = set(), self.browse()
        for membership in existing:
            key = (membership.team_id.id, membership.user_id.id)
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
                        "%s (%s)" % (m.user_id.name, m.team_id.name) for m in duplicates
                    ),
                )
            )

    @api.constrains("team_id", "user_id", "active")
    def _constrains_company_membership(self):
        self._check_company_membership()

    @api.constrains("team_id", "user_id", "active")
    def _constrains_live_endpoints(self):
        for membership in self.filtered("active"):
            if not membership.team_id.active:
                raise exceptions.ValidationError(
                    _(
                        "Team '%(team)s' is archived and cannot take new members.",
                        team=membership.team_id.name,
                    )
                )
            if not membership.user_id.active:
                raise exceptions.ValidationError(
                    _(
                        "User '%(user)s' is archived and cannot join a team.",
                        user=membership.user_id.name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        memberships = super(
            TeamMember, self.with_context(mail_create_nosubscribe=True)
        ).create(vals_list)
        memberships._on_membership_changed()
        return memberships

    def write(self, vals):
        res = super().write(vals)
        if vals.keys() & {"active", "user_id", "team_id"}:
            self._on_membership_changed()
        return res

    def unlink(self):
        res = super().unlink()
        self._clear_membership_dependent_caches()
        return res

    @api.depends("team_id", "team_id.company_id")
    def _compute_user_company_ids(self):
        all_companies = self.env["res.company"].search([])
        for member in self:
            member.user_company_ids = member.team_id.company_id or all_companies

    @api.depends("active", "user_id", "team_id")
    def _compute_member_warning(self):
        active = self.filtered("active")
        (self - active).member_warning = False
        if not active:
            return

        teams_by_user = self._get_live_teams_by_user(active.user_id)
        for member in active:
            team = member.team_id
            if not team:
                member.member_warning = False
                continue
            remaining = team._filter_sharing_mono_usage(
                teams_by_user.get(member.user_id, self.env["team.team"])
                - (team | member._origin.team_id)
            )
            if remaining:
                member.member_warning = self._get_membership_warning(
                    [member.user_id.name], remaining
                )
            else:
                member.member_warning = False

    @api.model
    def _search_live_projection(
        self, membership_field, target_field, operator, value, live=None
    ):
        if operator in NEGATIVE_CONDITION_OPERATORS:
            return NotImplemented

        live = Domain("active", "=", True) & (live or Domain.TRUE)
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
        teams_by_user = dict.fromkeys(users, self.env["team.team"])
        if not users.ids:
            return teams_by_user
        for membership in self.search(
            [("active", "=", True), ("user_id", "in", users.ids)]
        ):
            teams_by_user[membership.user_id] |= membership.team_id
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
                and m.team_id.company_id
                and m.team_id.company_id not in m.user_id.company_ids
            )
        )
        if not foreign:
            return
        team = foreign.team_id[:1]
        raise exceptions.ValidationError(
            _(
                "The following team members are not allowed in company '%(company)s' of the team '%(team)s': %(users)s",
                company=team.company_id.display_name,
                team=team.name,
                users=", ".join(
                    foreign.filtered(lambda m: m.team_id == team).user_id.mapped("name")
                ),
            )
        )

    def _on_membership_changed(self):
        self._enforce_mono_membership()
        self._add_to_team_favorites()
        self._clear_membership_dependent_caches()

    def _add_to_team_favorites(self):
        for team, memberships in self.filtered("active").grouped("team_id").items():
            team.favorite_user_ids = [
                Command.link(user_id) for user_id in memberships.user_id.ids
            ]

    def _enforce_mono_membership(self):
        # the later of two memberships wins, whether it was created in this batch
        # or before; eviction is bookkeeping the joining user may not see or write
        active = self.filtered(lambda member: member.active and member.team_id)
        if not active:
            return
        Member = self.sudo()
        live = Member.search(
            [("active", "=", True), ("user_id", "in", active.user_id.ids)]
        )
        kept, obsolete = Member.browse(), Member.browse()
        for winner in active.sudo().sorted("id", reverse=True):
            if winner in obsolete:
                continue
            kept |= winner
            if not winner.team_id._get_mono_usage_keys():
                continue
            protected = kept
            obsolete |= live.filtered(
                lambda member, winner=winner, protected=protected: (
                    member.user_id == winner.user_id
                    and member not in protected
                    and member.team_id != winner.team_id
                    and winner.team_id._filter_sharing_mono_usage(member.team_id)
                )
            )
        if obsolete:
            _debug.logic("mono_membership_evicted", winners=self, evicted=obsolete)
            obsolete.action_archive()

    def _clear_membership_dependent_caches(self):
        _debug.logic("membership_caches_cleared", memberships=self)
        self.env.registry.clear_cache()
