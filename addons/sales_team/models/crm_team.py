from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import str2bool


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ["mixin.mail.thread", "mixin.user.favorite", "mixin.color"]
    _description = "Sales Team"
    _order = "sequence ASC, create_date DESC, id DESC"
    _check_company_auto = True

    def _default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    name = fields.Char("Sales Team", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(
        default=True,
        help="If the active field is set to false, it will allow you to hide the Sales Team without removing it.",
    )
    company_id = fields.Many2one("res.company", index=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Team Leader",
        check_company=True,
        domain=[("share", "!=", True)],
    )
    is_membership_multi = fields.Boolean(
        "Multiple Memberships Allowed",
        compute="_compute_is_membership_multi",
        help="If True, users may belong to several sales teams. Otherwise membership is limited to a single sales team.",
    )
    member_ids = fields.Many2many(
        "res.users",
        string="Salespersons",
        domain="['&', ('share', '=', False), ('company_ids', 'in', member_company_ids)]",
        compute="_compute_member_ids",
        inverse="_inverse_member_ids",
        search="_search_member_ids",
        help="Users assigned to this team.",
    )
    member_company_ids = fields.Many2many(
        "res.company",
        compute="_compute_member_company_ids",
        help="UX: Limit to team company or all if no company",
    )
    member_warning = fields.Text(
        "Membership Issue Warning", compute="_compute_member_warning"
    )
    crm_team_member_ids = fields.One2many(
        "crm.team.member",
        "crm_team_id",
        string="Sales Team Members",
        context={"active_test": True},
        help="Add members to automatically assign their documents to this sales team.",
    )
    crm_team_member_all_ids = fields.One2many(
        "crm.team.member",
        "crm_team_id",
        string="Sales Team Members (incl. inactive)",
        context={"active_test": False},
    )
    color = fields.Integer(
        string="Color Index",
        help="The color of the channel",
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
    dashboard_button_name = fields.Char(
        string="Dashboard Button", compute="_compute_dashboard_button_name"
    )

    @api.constrains("company_id")
    def _constrains_company_members(self):
        for team in self.filtered("company_id"):
            invalid_members = team.crm_team_member_ids.filtered(
                lambda m, team=team: team.company_id not in m.user_id.company_ids
            )
            if invalid_members:
                raise ValidationError(
                    _(
                        "The following team members are not allowed in company '%(company)s' of the Sales Team '%(team)s': %(users)s",
                        company=team.company_id.display_name,
                        team=team.name,
                        users=", ".join(invalid_members.mapped("user_id.name")),
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        teams = super(CrmTeam, self.with_context(mail_create_nosubscribe=True)).create(
            vals_list
        )
        teams.crm_team_member_ids._add_to_team_favorites()
        return teams

    def write(self, vals):
        res = super().write(vals)
        if vals.get("active") is False:
            self.crm_team_member_ids.action_archive()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default(self):
        default_teams = self.browse()
        for xmlid in (
            "sales_team.team_sales_department",
            "sales_team.salesteam_website_sales",
            "sales_team.pos_sales_team",
        ):
            default_teams |= (
                self.env.ref(xmlid, raise_if_not_found=False) or self.browse()
            )

        if protected := (self & default_teams):
            raise UserError(
                _('Cannot delete default team "%(name)s"', name=protected[0].name)
            )

    @api.depends()
    def _compute_is_membership_multi(self):
        self.is_membership_multi = self._is_membership_multi()

    @api.depends("crm_team_member_ids.active", "crm_team_member_ids.user_id")
    def _compute_member_ids(self):
        for team in self:
            team.member_ids = team.crm_team_member_ids.user_id

    @api.depends("is_membership_multi", "member_ids")
    def _compute_member_warning(self):
        self.member_warning = False
        teams = self.filtered(
            lambda team: not team.is_membership_multi and team.member_ids
        )
        if not teams:
            return

        teams_by_user = self.env["crm.team.member"]._get_live_teams_by_user(
            teams.member_ids
        )

        for team in teams:
            user_names, other_teams = [], self.env["crm.team"]
            for user in team.member_ids:
                elsewhere = teams_by_user.get(user, self.env["crm.team"]) - team._origin
                if elsewhere:
                    user_names.append(user.name)
                    other_teams |= elsewhere
            if user_names:
                team.member_warning = self.env[
                    "crm.team.member"
                ]._get_membership_warning(user_names, other_teams)

    @api.depends("company_id")
    def _compute_member_company_ids(self):
        all_companies = self.env["res.company"].search([])
        for team in self:
            team.member_company_ids = team.company_id or all_companies

    def _compute_dashboard_button_name(self):
        self.dashboard_button_name = _("Dashboard")

    def _search_member_ids(self, operator, value):
        return self.env["crm.team.member"]._search_live_projection(
            "crm_team_member_ids", "user_id", operator, value
        )

    def _inverse_member_ids(self):
        to_create, to_archive = [], self.env["crm.team.member"]
        for team in self:
            memberships = team.crm_team_member_ids
            users_current = team.member_ids

            to_create += [
                {"crm_team_id": team.id, "user_id": user.id}
                for user in users_current - memberships.user_id
            ]
            to_archive += memberships.filtered(
                lambda m, users_current=users_current: m.user_id not in users_current
            )

        if to_create:
            self.env["crm.team.member"].create(to_create)
        if to_archive:
            to_archive.action_archive()

    def action_primary_channel_button(self):
        return False

    @api.model
    def action_activate_multi_membership(self):
        if not self.env.user.has_group("sales_team.group_sale_manager"):
            raise AccessError(
                _(
                    "Only a Sales Administrator can allow multiple sales team memberships."
                )
            )
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )

    @api.model
    def _is_membership_multi(self):
        return str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sales_team.membership_multi", ""),
            default=False,
        )

    def _get_default_team_id(self, user_id=False, domain=()):
        user = (
            self.env["res.users"].sudo().browse(user_id) if user_id else self.env.user
        )
        context_team = self._get_context_default_team()
        live_teams = self._get_domain_live_teams(user)

        own_teams = self._get_live_teams_for_user(user, live_teams)
        preferred = own_teams.filtered_domain(domain) if domain else own_teams

        for candidates in (preferred, own_teams):
            if candidates:
                if context_team and context_team in candidates:
                    return context_team
                return candidates[:1]

        if context_team:
            return context_team

        return self._get_company_default_team(live_teams, domain)

    def _get_context_default_team(self):
        context_team_id = self.env.context.get("default_team_id")
        if not context_team_id:
            return self.browse()
        return self.browse(
            self.sudo()
            .search([("id", "=", context_team_id), ("active", "=", True)])
            .ids
        )

    def _get_domain_live_teams(self, user):
        valid_cids = [False] + [
            cid for cid in user.company_ids.ids if cid in self.env.companies.ids
        ]
        return [("active", "=", True), ("company_id", "in", valid_cids)]

    def _get_live_teams_for_user(self, user, live_teams):
        return self.browse(
            self.sudo()
            .search(
                [
                    *live_teams,
                    "|",
                    ("user_id", "=", user.id),
                    ("member_ids", "in", [user.id]),
                ]
            )
            .ids
        )

    def _get_company_default_team(self, live_teams, domain):
        teams = self.sudo()
        if domain:
            team = teams.search(live_teams + list(domain), limit=1)
            if team:
                return self.browse(team.ids)
        return self.browse(teams.search(live_teams, limit=1).ids)
