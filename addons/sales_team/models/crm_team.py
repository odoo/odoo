# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from babel.dates import format_date
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.release import version
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ['mail.thread']
    _description = "Sales Channel"
    _order = "name"

    @api.model
    @api.returns('self', lambda value: value.id if value else False)
    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        company_id = self.sudo(user_id).env.user.company_id.id
        team_id = self.env['crm.team'].sudo().search([
            '|', ('user_id', '=', user_id), ('member_ids', '=', user_id),
            '|', ('company_id', '=', False), ('company_id', 'child_of', [company_id])
        ], limit=1)
        if not team_id and 'default_team_id' in self.env.context:
            team_id = self.env['crm.team'].browse(self.env.context.get('default_team_id'))
        if not team_id:
            default_team_id = self.env.ref('sales_team.team_sales_department', raise_if_not_found=False)
            if default_team_id and (self.env.context.get('default_type') != 'lead' or default_team_id.use_leads):
                team_id = default_team_id
        return team_id

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    name = fields.Char('Sales Channel', required=True, translate=True)
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the sales channel without removing it.")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get('crm.team'))
    currency_id = fields.Many2one(
        "res.currency", related='company_id.currency_id',
        string="Currency", readonly=True)
    user_id = fields.Many2one('res.users', string='Channel Leader')
    member_ids = fields.One2many('res.users', 'sale_team_id', string='Channel Members')
    favorite_user_ids = fields.Many2many(
        'res.users', 'team_favorite_user_rel', 'team_id', 'user_id',
        string='Favorite Members',
        default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        string='Show on dashboard',
        compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")
    reply_to = fields.Char(string='Reply-To',
                           help="The email address put in the 'Reply-To' of all emails sent by Odoo about cases in this sales channel")
    color = fields.Integer(string='Color Index', help="The color of the channel")
    team_type = fields.Selection([('sales', 'Sales'), ('website', 'Website')], string='Channel Type', default='sales', required=True,
                                 help="The type of this channel, it will define the resources this channel uses.")
    dashboard_button_name = fields.Char(string="Dashboard Button", compute='_compute_dashboard_button_name')
    dashboard_graph_data = fields.Text(compute='_compute_dashboard_graph')
    dashboard_graph_type = fields.Selection([
        ('line', 'Line'),
        ('bar', 'Bar'),
    ], string='Type', compute='_compute_dashboard_graph', help='The type of graph this channel will display in the dashboard.')
    dashboard_graph_model = fields.Selection([], string="Content", help='The graph this channel will display in the Dashboard.\n')
    dashboard_graph_group = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('user', 'Salesperson'),
    ], string='Group by', default='day', help="How this channel's dashboard graph will group the results.")
    dashboard_graph_period = fields.Selection([
        ('week', 'Last Week'),
        ('month', 'Last Month'),
        ('year', 'Last Year'),
    ], string='Scale', default='month', help="The time period this channel's dashboard graph will consider.")

    @api.depends('dashboard_graph_group', 'dashboard_graph_model', 'dashboard_graph_period')
    def _compute_dashboard_graph(self):
        for team in self.filtered('dashboard_graph_model'):
            if team.dashboard_graph_group in (False, 'user') or team.dashboard_graph_period == 'week' and team.dashboard_graph_group != 'day' \
                    or team.dashboard_graph_period == 'month' and team.dashboard_graph_group != 'day':
                team.dashboard_graph_type = 'bar'
            else:
                team.dashboard_graph_type = 'line'
            team.dashboard_graph_data = json.dumps(team._get_graph())

    def _compute_is_favorite(self):
        for team in self:
            team.is_favorite = self.env.user in team.favorite_user_ids

    def _inverse_is_favorite(self):
        sudoed_self = self.sudo()
        to_fav = sudoed_self.filtered(lambda team: self.env.user not in team.favorite_user_ids)
        to_fav.write({'favorite_user_ids': [(4, self.env.uid)]})
        (sudoed_self - to_fav).write({'favorite_user_ids': [(3, self.env.uid)]})
        return True

    def _graph_get_dates(self, today):
        """ return a coherent start and end date for the dashboard graph according to the graph settings.
        """
        if self.dashboard_graph_period == 'week':
            start_date = today - relativedelta(weeks=1)
        elif self.dashboard_graph_period == 'year':
            start_date = today - relativedelta(years=1)
        else:
            start_date = today - relativedelta(months=1)

        # we take the start of the following month/week/day if we group by month/week/day
        # (to avoid having twice the same month/week/day from different years/month/week)
        if self.dashboard_graph_group == 'month':
            start_date = date(start_date.year + start_date.month // 12, start_date.month % 12 + 1, 1)
            # handle period=week, grouping=month for silly managers
            if self.dashboard_graph_period == 'week':
                start_date = today.replace(day=1)
        elif self.dashboard_graph_group == 'week':
            start_date += relativedelta(days=8 - start_date.isocalendar()[2])
            # add a week to make sure no overlapping is possible in case of year period (will display max 52 weeks, avoid case of 53 weeks in a year)
            if self.dashboard_graph_period == 'year':
                start_date += relativedelta(weeks=1)
        else:
            start_date += relativedelta(days=1)

        return [start_date, today]

    def _graph_date_column(self):
        return 'create_date'

    def _graph_x_query(self):
        if self.dashboard_graph_group == 'user':
            return 'user_id'
        elif self.dashboard_graph_group == 'week':
            return 'EXTRACT(WEEK FROM %s)' % self._graph_date_column()
        elif self.dashboard_graph_group == 'month':
            return 'EXTRACT(MONTH FROM %s)' % self._graph_date_column()
        else:
            return 'DATE(%s)' % self._graph_date_column()

    def _graph_y_query(self):
        raise UserError(_('Undefined graph model for Sales Channel: %s') % self.name)

    def _extra_sql_conditions(self):
        return ''

    def _graph_title_and_key(self):
        """ Returns an array containing the appropriate graph title and key respectively.

            The key is for lineCharts, to have the on-hover label.
        """
        return ['', '']

    def _graph_data(self, start_date, end_date):
        """ return format should be an iterable of dicts that contain {'x_value': ..., 'y_value': ...}
            x_values should either be dates, weeks, months or user_ids depending on the self.dashboard_graph_group value.
            y_values are floats.
        """
        query = """SELECT %(x_query)s as x_value, %(y_query)s as y_value
                     FROM %(table)s
                    WHERE team_id = %(team_id)s
                      AND DATE(%(date_column)s) >= %(start_date)s
                      AND DATE(%(date_column)s) <= %(end_date)s
                      %(extra_conditions)s
                    GROUP BY x_value;"""

        # apply rules
        if not self.dashboard_graph_model:
            raise UserError(_('Undefined graph model for Sales Channel: %s') % self.name)
        GraphModel = self.env[self.dashboard_graph_model]
        graph_table = GraphModel._table
        extra_conditions = self._extra_sql_conditions()
        where_query = GraphModel._where_calc([])
        GraphModel._apply_ir_rules(where_query, 'read')
        from_clause, where_clause, where_clause_params = where_query.get_sql()
        if where_clause:
            extra_conditions += " AND " + where_clause

        query = query % {
            'x_query': self._graph_x_query(),
            'y_query': self._graph_y_query(),
            'table': graph_table,
            'team_id': "%s",
            'date_column': self._graph_date_column(),
            'start_date': "%s",
            'end_date': "%s",
            'extra_conditions': extra_conditions
        }
        self._cr.execute(query, [self.id, start_date, end_date] + where_clause_params)
        return self.env.cr.dictfetchall()

    def _get_graph(self):
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
        today = date.today()
        start_date, end_date = self._graph_get_dates(today)
        graph_data = self._graph_data(start_date, end_date)

        # line graphs and bar graphs require different labels
        if self.dashboard_graph_type == 'line':
            x_field = 'x'
            y_field = 'y'
        else:
            x_field = 'label'
            y_field = 'value'

        # generate all required x_fields and update the y_values where we have data for them
        locale = self._context.get('lang') or 'en_US'
        if self.dashboard_graph_group == 'day':
            for day in range(0, (end_date - start_date).days + 1):
                short_name = format_date(start_date + relativedelta(days=day), 'd MMM', locale=locale)
                values.append({x_field: short_name, y_field: 0})
            for data_item in graph_data:
                index = (datetime.strptime(data_item.get('x_value'), DF).date() - start_date).days
                values[index][y_field] = data_item.get('y_value')

        elif self.dashboard_graph_group == 'week':
            weeks_in_start_year = int(date(start_date.year, 12, 28).isocalendar()[1]) # This date is always in the last week of ISO years
            for week in range(0, (end_date.isocalendar()[1] - start_date.isocalendar()[1]) % weeks_in_start_year + 1):
                short_name = get_week_name(start_date + relativedelta(days=7 * week), locale)
                values.append({x_field: short_name, y_field: 0})

            for data_item in graph_data:
                index = int((data_item.get('x_value') - start_date.isocalendar()[1]) % weeks_in_start_year)
                values[index][y_field] = data_item.get('y_value')

        elif self.dashboard_graph_group == 'month':
            for month in range(0, (end_date.month - start_date.month) % 12 + 1):
                short_name = format_date(start_date + relativedelta(months=month), 'MMM', locale=locale)
                values.append({x_field: short_name, y_field: 0})

            for data_item in graph_data:
                index = int((data_item.get('x_value') - start_date.month) % 12)
                values[index][y_field] = data_item.get('y_value')

        elif self.dashboard_graph_group == 'user':
            for data_item in graph_data:
                values.append({x_field: self.env['res.users'].browse(data_item.get('x_value')).name or _('Not Defined'), y_field: data_item.get('y_value')})

        else:
            for data_item in graph_data:
                values.append({x_field: data_item.get('x_value'), y_field: data_item.get('y_value')})

        [graph_title, graph_key] = self._graph_title_and_key()
        color = '#875A7B' if '+e' in version else '#7c7bad'
        return [{'values': values, 'area': True, 'title': graph_title, 'key': graph_key, 'color': color}]

    def _compute_dashboard_button_name(self):
        """ Sets the adequate dashboard button name depending on the sales channel's options
        """
        for team in self:
            team.dashboard_button_name = _("Big Pretty Button :)") # placeholder

    def action_primary_channel_button(self):
        """ skeleton function to be overloaded
            It will return the adequate action depending on the sales channel's options
        """
        return False

    def _onchange_team_type(self):
        """ skeleton function defined here because it'll be called by crm and/or sale
        """
        self.ensure_one()

    @api.model
    def create(self, values):
        team = super(CrmTeam, self.with_context(mail_create_nosubscribe=True)).create(values)
        if values.get('member_ids'):
            team._add_members_to_favorites()
        return team

    @api.multi
    def write(self, values):
        res = super(CrmTeam, self).write(values)
        if values.get('member_ids'):
            self._add_members_to_favorites()
        return res

    def _add_members_to_favorites(self):
        for team in self:
            team.favorite_user_ids = [(4, member.id) for member in team.member_ids]
