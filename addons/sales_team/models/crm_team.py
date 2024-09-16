# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import random

from babel.dates import format_date
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.release import version
from odoo.tools import SQL


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ['mail.thread']
    _description = "Sales Team"
    _order = "sequence ASC, create_date DESC, id DESC"
    _check_company_auto = True

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
        :domain: optional domain to filter teams (like use_lead = True);
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
    user_id = fields.Many2one('res.users', string='Team Leader', check_company=True)
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
    color = fields.Integer(string='Color Index', help="The color of the channel")
    favorite_user_ids = fields.Many2many(
        'res.users', 'team_favorite_user_rel', 'team_id', 'user_id',
        string='Favorite Members', default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        string='Show on dashboard', compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")
    dashboard_button_name = fields.Char(string="Dashboard Button", compute='_compute_dashboard_button_name')
    dashboard_graph_data = fields.Text(compute='_compute_dashboard_graph')

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
            member_warning = False
            other_memberships = self.env['crm.team.member'].search([
                ('crm_team_id', '!=', team.id if team.ids else False),  # handle NewID
                ('user_id', 'in', team.member_ids.ids)
            ])
            if other_memberships and len(other_memberships) == 1:
                member_warning = _("Adding %(user_name)s in this team would remove him/her from its current team %(team_name)s.",
                                   user_name=other_memberships.user_id.name,
                                   team_name=other_memberships.crm_team_id.name
                                  )
            elif other_memberships:
                member_warning = _("Adding %(user_names)s in this team would remove them from their current teams (%(team_names)s).",
                                   user_names=", ".join(other_memberships.mapped('user_id.name')),
                                   team_names=", ".join(other_memberships.mapped('crm_team_id.name'))
                                  )
            if member_warning:
                team.member_warning = member_warning + " " + _("To add a Salesperson into multiple Teams, activate the Multi-Team option in settings.")

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

    def _compute_dashboard_graph(self):
        for team in self:
            team.dashboard_graph_data = json.dumps(team._get_dashboard_graph_data())

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        teams = super(CrmTeam, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        teams.filtered(lambda t: t.member_ids)._add_members_to_favorites()
        return teams

    def write(self, values):
        res = super(CrmTeam, self).write(values)
        # manually launch company sanity check
        if values.get('company_id'):
            self.crm_team_member_ids._check_company(fnames=['crm_team_id'])

        if values.get('member_ids'):
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

    # ------------------------------------------------------------
    # GRAPH
    # ------------------------------------------------------------

    def _graph_get_model(self) -> str:
        """ skeleton function defined here because it'll be called by crm and/or sale
        """
        raise UserError(_('Undefined graph model for Sales Team: %s', self.name))

    def _graph_get_dates(self, today):
        """ return a coherent start and end date for the dashboard graph covering a month period grouped by week.
        """
        start_date = today - relativedelta(months=1)
        # we take the start of the following week if we group by week
        # (to avoid having twice the same week from different month)
        start_date += relativedelta(days=8 - start_date.isocalendar()[2])
        return [start_date, today]

    def _graph_date_column(self) -> SQL:
        return SQL('create_date')

    def _graph_get_table(self, GraphModel) -> SQL:
        return SQL(GraphModel._table)

    def _graph_x_query(self) -> SQL:
        return SQL('EXTRACT(WEEK FROM %s)', self._graph_date_column())

    def _graph_y_query(self) -> SQL:
        raise UserError(_('Undefined graph model for Sales Team: %s', self.name))

    def _extra_sql_conditions(self) -> SQL:
        return SQL()

    def _graph_title_and_key(self):
        """ Returns an array containing the appropriate graph title and key respectively.

            The key is for lineCharts, to have the on-hover label.
        """
        return ['', '']

    def _graph_data(self, start_date, end_date):
        """ return format should be an iterable of dicts that contain {'x_value': ..., 'y_value': ...}
            x_values should be weeks.
            y_values are floats.
        """
        # apply rules
        extra_conditions = self._extra_sql_conditions() or SQL("TRUE")
        dashboard_graph_model = self._graph_get_model()
        GraphModel = self.env[dashboard_graph_model]
        where_query = GraphModel._where_calc([])
        GraphModel._apply_ir_rules(where_query, 'read')
        if where_clause := where_query.where_clause:
            extra_conditions = SQL("%s AND (%s)", extra_conditions, where_clause)

        sql = SQL(
            """
            SELECT %(x_query)s as x_value, %(y_query)s as y_value
            FROM %(table)s
            WHERE team_id = %(team_id)s
                AND DATE(%(date_column)s) >= %(start_date)s
                AND DATE(%(date_column)s) <= %(end_date)s
                AND %(extra_conditions)s
            GROUP BY x_value
            """,
            x_query=self._graph_x_query(),
            y_query=self._graph_y_query(),
            table=self._graph_get_table(GraphModel),
            team_id=self.id,
            date_column=self._graph_date_column(),
            start_date=start_date,
            end_date=end_date,
            extra_conditions=extra_conditions,
        )

        self._cr.execute(sql)
        return self.env.cr.dictfetchall()

    def _get_dashboard_graph_data(self):
        def get_week_name(start_date, locale):
            """ Generates a week name (string) from a datetime according to the locale:
                E.g.: locale    start_date (datetime)      return string
                      "en_US"      November 16th           "16-22 Nov"
                      "en_US"      December 28th           "28 Dec-3 Jan"
            """
            if (start_date + relativedelta(days=6)).month == start_date.month:
                short_name_from = format_date(start_date, 'd', locale=locale)
            else:
                short_name_from = format_date(start_date, 'd MMM', locale=locale)
            short_name_to = format_date(start_date + relativedelta(days=6), 'd MMM', locale=locale)
            return short_name_from + '-' + short_name_to

        self.ensure_one()
        values = []
        today = fields.Date.from_string(fields.Date.context_today(self))
        start_date, end_date = self._graph_get_dates(today)
        graph_data = self._graph_data(start_date, end_date)
        x_field = 'label'
        y_field = 'value'

        # generate all required x_fields and update the y_values where we have data for them
        locale = self._context.get('lang') or 'en_US'

        weeks_in_start_year = int(date(start_date.year, 12, 28).isocalendar()[1]) # This date is always in the last week of ISO years
        week_count = (end_date.isocalendar()[1] - start_date.isocalendar()[1]) % weeks_in_start_year + 1
        for week in range(week_count):
            short_name = get_week_name(start_date + relativedelta(days=7 * week), locale)
            values.append({x_field: short_name, y_field: 0, 'type': 'future' if week + 1 == week_count else 'past'})

        for data_item in graph_data:
            index = int((data_item.get('x_value') - start_date.isocalendar()[1]) % weeks_in_start_year)
            values[index][y_field] = data_item.get('y_value')

        [graph_title, graph_key] = self._graph_title_and_key()
        color = '#875A7B' if '+e' in version else '#7c7bad'

        # If no actual data available, show some sample data
        if not graph_data:
            graph_key = _('Sample data')
            for value in values:
                value['type'] = 'o_sample_data'
                # we use unrealistic values for the sample data
                value['value'] = random.randint(0, 20)
        return [{'values': values, 'area': True, 'title': graph_title, 'key': graph_key, 'color': color}]
