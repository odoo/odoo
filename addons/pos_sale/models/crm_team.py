# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    team_type = fields.Selection(selection_add=[('pos', 'Point of Sale')])
    pos_config_ids = fields.One2many('pos.config', 'crm_team_id', string="Point of Sales")
    pos_sessions_open_count = fields.Integer(string='Open POS Sessions', compute='_compute_pos_sessions_open_count')
    pos_order_amount_total = fields.Float(string="Session Sale Amount", compute='_compute_pos_order_amount_total')
    dashboard_graph_group_pos = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('user', 'Salesperson'),
        ('pos', 'Point of Sale'),
    ], string='Group by', default='day', help="How this channel's dashboard graph will group the results.")

    @api.onchange('dashboard_graph_group_pos')
    def _onchange_dashboard_graph_group_pos(self):
        if self.dashboard_graph_group_pos == 'pos':
            self.dashboard_graph_group = False
        else:
            self.dashboard_graph_group = self.dashboard_graph_group_pos

    def _compute_pos_sessions_open_count(self):
        for team in self.filtered(lambda t: t.team_type == 'pos'):
            team.pos_sessions_open_count = self.env['pos.session'].search_count([('config_id.crm_team_id', '=', team.id), ('state', '=', 'opened')])

    def _compute_pos_order_amount_total(self):
        for team in self.filtered(lambda t: t.team_type == 'pos'):
            team.pos_order_amount_total = sum(self.env['report.pos.order'].search(
                [('session_id', 'in', team.pos_config_ids.mapped('session_ids').filtered(lambda s: s.state == 'opened').ids)]
            ).mapped('price_total'))

    def _graph_data(self, start_date, end_date):
        """ If the type of the sales team is point of sale ('pos'), the graph will display the sales data.
            The override here is to get data from pos.order instead of sale.order.
        """
        if self.team_type == 'pos':
            result = []
            if self.dashboard_graph_group_pos == 'pos':
                order_data = self.env['report.pos.order'].read_group(
                    domain=[
                        ('date', '>=', fields.Date.to_string(start_date)),
                        ('date', '<=', fields.Datetime.to_string(datetime.combine(end_date, datetime.max.time()))),
                        ('config_id', 'in', self.pos_config_ids.ids),
                        ('state', 'in', ['paid', 'done', 'invoiced'])],
                    fields=['config_id', 'price_total'],
                    groupby=['config_id']
                )
                appended_config_ids = set()
                for data_point in order_data:
                    result.append({'x_value': self.env['pos.config'].browse(data_point.get('config_id')[0]).name, 'y_value': data_point.get('price_total')})
                    appended_config_ids.add(data_point.get('config_id'))
                for config_id in set(self.pos_config_ids.ids) - appended_config_ids:
                    result.append({'x_value': self.env['pos.config'].browse(config_id).name, 'y_value': 0})

            elif self.dashboard_graph_group_pos == 'user':
                order_data = self.env['report.pos.order'].read_group(
                    domain=[
                        ('date', '>=', fields.Date.to_string(start_date)),
                        ('date', '<=', fields.Datetime.to_string(datetime.combine(end_date, datetime.max.time()))),
                        ('config_id', 'in', self.pos_config_ids.ids),
                        ('state', 'in', ['paid', 'done', 'invoiced'])],
                    fields=['user_id', 'price_total'],
                    groupby=['user_id']
                )
                for data_point in order_data:
                    result.append({'x_value': data_point.get('user_id')[0], 'y_value': data_point.get('price_total')})

            else:
                # locale en_GB is used to be able to obtain the datetime from the string returned by read_group
                # /!\ do not use en_US as it's not ISO-standard and does not match datetime's library
                order_data = self.env['report.pos.order'].with_context(lang='en_GB').read_group(
                    domain=[
                        ('date', '>=', fields.Date.to_string(start_date)),
                        ('date', '<=', fields.Datetime.to_string(datetime.combine(end_date, datetime.max.time()))),
                        ('config_id', 'in', self.pos_config_ids.ids),
                        ('state', 'in', ['paid', 'done', 'invoiced'])],
                    fields=['date', 'price_total'],
                    groupby=['date:' + self.dashboard_graph_group_pos]
                )
                if self.dashboard_graph_group_pos == 'day':
                    for data_point in order_data:
                        result.append({'x_value': fields.Date.to_string((fields.datetime.strptime(data_point.get('date:day'), "%d %b %Y"))), 'y_value': data_point.get('price_total')})
                elif self.dashboard_graph_group_pos == 'week':
                    for data_point in order_data:
                        result.append({'x_value': int(data_point.get('date:week')[1:3]), 'y_value': data_point.get('price_total')})
                elif self.dashboard_graph_group_pos == 'month':
                    for data_point in order_data:
                        result.append({'x_value': fields.datetime.strptime(data_point.get('date:month'), "%B %Y").month, 'y_value': data_point.get('price_total')})
            return result

        return super(CrmTeam, self)._graph_data(start_date, end_date)

    def _compute_dashboard_button_name(self):
        pos_teams = self.filtered(lambda team: team.team_type == 'pos')
        pos_teams.update({'dashboard_button_name': _("Dashboard")})
        super(CrmTeam, self - pos_teams)._compute_dashboard_button_name()

    def action_primary_channel_button(self):
        if self.team_type == 'pos':
            action = self.env.ref('point_of_sale.action_pos_config_kanban').read()[0]
            action['context'] = {'search_default_crm_team_id': self.id}
            return action
        return super(CrmTeam, self).action_primary_channel_button()

    def _graph_title_and_key(self):
        if self.team_type == 'pos':
            return ['', _('Sales: Untaxed Amount')] # no more title
        return super(CrmTeam, self)._graph_title_and_key()
