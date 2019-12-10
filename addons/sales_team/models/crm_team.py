# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from babel.dates import format_date
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import json

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.release import version
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class CrmTeam(models.Model):
    _name = "crm.team"
    _inherit = ['mail.thread']
    _description = "Sales Team"
    _order = "sequence"
    _check_company_auto = True

    @api.model
    @api.returns('self', lambda value: value.id if value else False)
    def _get_default_team_id(self, user_id=None, domain=None):
        if not user_id:
            user_id = self.env.uid
        team_id = self.env['crm.team'].search([
            '|', ('user_id', '=', user_id), ('member_ids', '=', user_id),
            '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not team_id and 'default_team_id' in self.env.context:
            team_id = self.env['crm.team'].browse(self.env.context.get('default_team_id'))
        if not team_id:
            team_domain = domain or []
            default_team_id = self.env['crm.team'].search(team_domain, limit=1)
            return default_team_id or self.env['crm.team']
        return team_id

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    name = fields.Char('Sales Team', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the Sales Team without removing it.")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(
        "res.currency", related='company_id.currency_id',
        string="Currency", readonly=True)
    user_id = fields.Many2one('res.users', string='Team Leader', check_company=True)
    member_ids = fields.One2many(
        'res.users', 'sale_team_id', string='Channel Members', check_company=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('base.group_user').id)],
        help="Add members to automatically assign their documents to this sales team. You can only be member of one team.")
    favorite_user_ids = fields.Many2many(
        'res.users', 'team_favorite_user_rel', 'team_id', 'user_id',
        string='Favorite Members',
        default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        string='Show on dashboard',
        compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        help="Favorite teams to display them in the dashboard and access them easily.")
    color = fields.Integer(string='Color Index', help="The color of the channel")
    dashboard_button_name = fields.Char(string="Dashboard Button", compute='_compute_dashboard_button_name')
    dashboard_graph_data = fields.Text(compute='_compute_dashboard_graph')

    def _compute_dashboard_graph(self):
        for team in self:
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

    def _graph_get_model(self):
        """ skeleton function defined here because it'll be called by crm and/or sale
        """
        raise UserError(_('Undefined graph model for Sales Team: %s') % self.name)

    def _graph_get_dates(self, today):
        """ return a coherent start and end date for the dashboard graph covering a month period grouped by week.
        """
        start_date = today - relativedelta(months=1)
        # we take the start of the following week if we group by week
        # (to avoid having twice the same week from different month)
        start_date += relativedelta(days=8 - start_date.isocalendar()[2])
        return [start_date, today]

    def _graph_date_column(self):
        return 'create_date'

    def _graph_x_query(self):
        return 'EXTRACT(WEEK FROM %s)' % self._graph_date_column()

    def _graph_y_query(self):
        raise UserError(_('Undefined graph model for Sales Team: %s') % self.name)

    def _extra_sql_conditions(self):
        return ''

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
        query = """SELECT %(x_query)s as x_value, %(y_query)s as y_value
                     FROM %(table)s
                    WHERE team_id = %(team_id)s
                      AND DATE(%(date_column)s) >= %(start_date)s
                      AND DATE(%(date_column)s) <= %(end_date)s
                      %(extra_conditions)s
                    GROUP BY x_value;"""

        # apply rules
        dashboard_graph_model = self._graph_get_model()
        GraphModel = self.env[dashboard_graph_model]
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
        today = fields.Date.from_string(fields.Date.context_today(self))
        start_date, end_date = self._graph_get_dates(today)
        graph_data = self._graph_data(start_date, end_date)
        x_field = 'label'
        y_field = 'value'

        # generate all required x_fields and update the y_values where we have data for them
        locale = self._context.get('lang') or 'en_US'

        weeks_in_start_year = int(date(start_date.year, 12, 28).isocalendar()[1]) # This date is always in the last week of ISO years
        for week in range(0, (end_date.isocalendar()[1] - start_date.isocalendar()[1]) % weeks_in_start_year + 1):
            short_name = get_week_name(start_date + relativedelta(days=7 * week), locale)
            values.append({x_field: short_name, y_field: 0})

        for data_item in graph_data:
            index = int((data_item.get('x_value') - start_date.isocalendar()[1]) % weeks_in_start_year)
            values[index][y_field] = data_item.get('y_value')

        [graph_title, graph_key] = self._graph_title_and_key()
        color = '#875A7B' if '+e' in version else '#7c7bad'
        return [{'values': values, 'area': True, 'title': graph_title, 'key': graph_key, 'color': color}]

    def _compute_dashboard_button_name(self):
        """ Sets the adequate dashboard button name depending on the Sales Team's options
        """
        for team in self:
            team.dashboard_button_name = _("Big Pretty Button :)") # placeholder

    def action_primary_channel_button(self):
        """ skeleton function to be overloaded
            It will return the adequate action depending on the Sales Team's options
        """
        return False

    @api.model
    def create(self, values):
        team = super(CrmTeam, self.with_context(mail_create_nosubscribe=True)).create(values)
        if values.get('member_ids'):
            team._add_members_to_favorites()
        return team

    def write(self, values):
        res = super(CrmTeam, self).write(values)
        if values.get('member_ids'):
            self._add_members_to_favorites()
        return res

    def unlink(self):
        default_teams = [
            self.env.ref('sales_team.salesteam_website_sales'),
            self.env.ref('sales_team.pos_sales_team'),
            self.env.ref('sales_team.ebay_sales_team')
        ]
        for team in self:
            if team in default_teams:
                raise UserError(_('Cannot delete default team "%s"' % (team.name)))
        return super(CrmTeam,self).unlink()

    def _add_members_to_favorites(self):
        for team in self:
            team.favorite_user_ids = [(4, member.id) for member in team.member_ids]
