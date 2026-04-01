import random

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrmTeam(models.Model):
    _name = 'crm.team'
    _inherit = ['mail.thread']
    _description = "Sales Team"
    _order = "sequence ASC, create_date DESC, id DESC"
    _check_company_auto = True

    def _get_default_color(self):
        return random.randint(1, 11)

    def _get_default_team_id(self, user_id=False, domain=False):
        """ Compute default team id for sales related documents. Note that this
        method is not called by default_get as it takes some additional
        parameters and is meant to be called by other default methods.

        Heuristic (when multiple match: take from default context value or first
        sequence ordered)

          1- any of my teams (member OR responsible) matching domain, either from
             context or based on _order;
          2- any of my teams (member OR responsible), either from context or based
             on _order;
          3- default from context
          4- any team matching my company and domain (based on company rule)
          5- any team matching my company (based on company rule)

        :param user_id: salesperson to target, fallback on env.uid;
        :param domain: optional domain to filter teams (like use_lead = True);
        """
        if not user_id:
            user = self.env.user
        else:
            user = self.env['res.users'].sudo().browse(user_id)
        default_team = self.env['crm.team'].browse(
            self.env.context['default_team_id']
        ) if self.env.context.get('default_team_id') else self.env['crm.team']
        valid_cids = [False] + [c for c in user.company_ids.ids if c in self.env.companies.ids]

        # 1- find in user memberships - note that if current user in C1 searches
        # for team belonging to a user in C1/C2 -> only results for C1 will be returned
        team = self.env['crm.team']
        teams = self.env['crm.team'].search([
            ('company_id', 'in', valid_cids),
             '|', ('user_id', '=', user.id), ('member_ids', 'in', [user.id])
        ])
        if teams and domain:
            filtered_teams = teams.filtered_domain(domain)
            if default_team and default_team in filtered_teams:
                team = default_team
            else:
                team = filtered_teams[:1]

        # 2- any of my teams
        if not team:
            if default_team and default_team in teams:
                team = default_team
            else:
                team = teams[:1]

        # 3- default: context
        if not team and default_team:
            team = default_team

        if not team:
            teams = self.env['crm.team'].search([('company_id', 'in', valid_cids)])
            # 4- default: based on company rule, first one matching domain
            if teams and domain:
                team = teams.filtered_domain(domain)[:1]
            # 5- default: based on company rule, first one
            if not team:
                team = teams[:1]

        return team

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    # description
    name = fields.Char('Sales Team', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the Sales Team without removing it.")
    company_id = fields.Many2one(
        'res.company', string='Company', index=True)
    currency_id = fields.Many2one(
        "res.currency", string="Currency",
        related='company_id.currency_id', readonly=True)
    user_id = fields.Many2one('res.users', string='Team Leader', check_company=True, domain=[('share', '!=', True)])
    # memberships
    is_membership_multi = fields.Boolean(
        'Multiple Memberships Allowed', compute='_compute_is_membership_multi',
        help='If True, users may belong to several sales teams. Otherwise membership is limited to a single sales team.')
    member_ids = fields.Many2many(
        'res.users', string='Salespersons',
        domain="['&', ('share', '=', False), ('company_ids', 'in', member_company_ids)]",
        compute='_compute_member_ids', inverse='_inverse_member_ids', search='_search_member_ids',
        help="Users assigned to this team.")
    member_company_ids = fields.Many2many(
        'res.company', compute='_compute_member_company_ids',
        help='UX: Limit to team company or all if no company')
    member_warning = fields.Text('Membership Issue Warning', compute='_compute_member_warning')
    crm_team_member_ids = fields.One2many(
        'crm.team.member', 'crm_team_id', string='Sales Team Members',
        context={'active_test': True},
        help="Add members to automatically assign their documents to this sales team.")
    crm_team_member_all_ids = fields.One2many(
        'crm.team.member', 'crm_team_id', string='Sales Team Members (incl. inactive)',
        context={'active_test': False})
    # UX options
    color = fields.Integer(string='Color Index', help="The color of the channel", default=_get_default_color)
    favorite_user_ids = fields.Many2many(
        'res.users', 'team_favorite_user_rel', 'team_id', 'user_id',
        string='Favorite Members', default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        string='Show on dashboard', compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")
    dashboard_button_name = fields.Char(string="Dashboard Button", compute='_compute_dashboard_button_name')

    @api.constrains('company_id')
    def _constrains_company_members(self):
        for team in self.filtered('company_id'):
            invalid_members = team.crm_team_member_ids.filtered(
                lambda m: team.company_id not in m.user_id.company_ids
            )
            if invalid_members:
                raise UserError(_("The following team members are not allowed in company '%(company)s' of the Sales Team '%(team)s': %(users)s",
                    company=team.company_id.display_name,
                    team=team.name,
                    users=", ".join(invalid_members.mapped('user_id.name'))
                ))

    @api.depends('sequence')  # TDE FIXME: force compute in new mode
    def _compute_is_membership_multi(self):
        multi_enabled = self.env['ir.config_parameter'].sudo().get_param('sales_team.membership_multi', False)
        self.is_membership_multi = multi_enabled

    @api.depends('crm_team_member_ids.active')
    def _compute_member_ids(self):
        for team in self:
            team.member_ids = team.crm_team_member_ids.user_id

    def _inverse_member_ids(self):
        for team in self:
            # pre-save value to avoid having _compute_member_ids interfering
            # while building membership status
            memberships = team.crm_team_member_ids
            users_current = team.member_ids
            users_new = users_current - memberships.user_id

            # add missing memberships
            self.env['crm.team.member'].create([{'crm_team_id': team.id, 'user_id': user.id} for user in users_new])

            # activate or deactivate other memberships depending on members
            for membership in memberships:
                membership.active = membership.user_id in users_current

    @api.depends('is_membership_multi', 'member_ids')
    def _compute_member_warning(self):
        """ Display a warning message to warn user they are about to archive
        other memberships. Only valid in mono-membership mode and take into
        account only active memberships as we may keep several archived
        memberships. """
        self.member_warning = False
        if all(team.is_membership_multi for team in self):
            return
        # done in a loop, but to be used in form view only -> not optimized
        for team in self:
            other_memberships = self.env['crm.team.member'].search([
                ('crm_team_id', '!=', team._origin.id if team.ids else False),
                ('user_id', 'in', team.member_ids.ids)
            ])
            if other_memberships:
                team.member_warning = _("%(user_names)s already in other teams (%(team_names)s).",
                                   user_names=", ".join(other_memberships.mapped('user_id.name')),
                                   team_names=", ".join(other_memberships.mapped('crm_team_id.name'))
                                  )

    def _search_member_ids(self, operator, value):
        return [('crm_team_member_ids.user_id', operator, value)]

    # 'name' should not be in the trigger, but as 'company_id' is possibly not present in the view
    # because it depends on the multi-company group, we use it as fake trigger to force computation
    @api.depends('company_id', 'name')
    def _compute_member_company_ids(self):
        """ Available companies for members. Either team company if set, either
        any company if not set on team. """
        all_companies = self.env['res.company'].search([])
        for team in self:
            team.member_company_ids = team.company_id or all_companies

    def _compute_is_favorite(self):
        for team in self:
            team.is_favorite = self.env.user in team.favorite_user_ids

    def _inverse_is_favorite(self):
        sudoed_self = self.sudo()
        to_fav = sudoed_self.filtered(lambda team: self.env.user not in team.favorite_user_ids)
        to_fav.write({'favorite_user_ids': [(4, self.env.uid)]})
        (sudoed_self - to_fav).write({'favorite_user_ids': [(3, self.env.uid)]})
        return True

    def _compute_dashboard_button_name(self):
        """ Sets the adequate dashboard button name depending on the Sales Team's options
        """
        for team in self:
            team.dashboard_button_name = _("Big Pretty Button :)") # placeholder

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        teams = super(CrmTeam, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        teams.filtered(lambda t: t.member_ids)._add_members_to_favorites()
        return teams

    def write(self, vals):
        res = super().write(vals)

        if vals.get('company_id'):  # Force re-check of memberships constraint for this team
            self.crm_team_member_ids._constrains_membership()

        if vals.get('member_ids'):
            self._add_members_to_favorites()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default(self):
        default_teams = [
            self.env.ref('sales_team.salesteam_website_sales'),
            self.env.ref('sales_team.pos_sales_team'),
        ]
        for team in self:
            if team in default_teams:
                raise UserError(_('Cannot delete default team "%s"', team.name))

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_primary_channel_button(self):
        """ Skeleton function to be overloaded It will return the adequate action
        depending on the Sales Team's options. """
        return False

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _add_members_to_favorites(self):
        for team in self:
            team.favorite_user_ids = [(4, member.id) for member in team.member_ids]
