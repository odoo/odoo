# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError


class Team(models.Model):
    _name = 'crm.team'
    _inherit = ['mail.alias.mixin', 'crm.team']

    use_leads = fields.Boolean('Leads', help="Check this box to filter and qualify incoming requests as leads before converting them into opportunities and assigning them to a salesperson.")
    use_opportunities = fields.Boolean('Pipeline', help="Check this box to manage a presales process with opportunities.")
    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True, help="The email address associated with this channel. New emails received will automatically create new leads assigned to the channel.")
    unassigned_leads_count = fields.Integer(
        compute='_compute_unassigned_leads_count',
        string='Unassigned Leads', readonly=True)
    opportunities_count = fields.Integer(
        compute='_compute_opportunities',
        string='Number of open opportunities', readonly=True)
    opportunities_amount = fields.Integer(
        compute='_compute_opportunities',
        string='Amount of quotations to invoice', readonly=True)
    dashboard_graph_model = fields.Selection(selection_add=[('pipeline', 'Pipeline')])

    def _compute_unassigned_leads_count(self):
        leads_data = self.env['crm.lead'].read_group([
            ('team_id', 'in', self.ids),
            ('type', '=', 'lead'),
            ('user_id', '=', False),
        ], ['team_id'], ['team_id'])
        counts = dict((data['team_id'][0], data['team_id_count']) for data in leads_data)
        for team in self:
            team.unassigned_leads_count = counts.get(team.id, 0)

    def _compute_opportunities(self):
        opportunity_data = self.env['crm.opportunity.report'].read_group([
            ('team_id', 'in', self.ids),
            ('probability', '<', 100),
            ('type', '=', 'opportunity'),
        ], ['expected_revenue', 'team_id'], ['team_id'])
        counts = dict((data['team_id'][0], data['team_id_count']) for data in opportunity_data)
        amounts = dict((data['team_id'][0], data['expected_revenue']) for data in opportunity_data)
        for team in self:
            team.opportunities_count = counts.get(team.id, 0)
            team.opportunities_amount = amounts.get(team.id, 0)

    def get_alias_model_name(self, vals):
        return 'crm.lead'

    def get_alias_values(self):
        has_group_use_lead = self.env.user.has_group('crm.group_use_lead')
        values = super(Team, self).get_alias_values()
        values['alias_defaults'] = defaults = safe_eval(self.alias_defaults or "{}")
        defaults['type'] = 'lead' if has_group_use_lead and self.use_leads else 'opportunity'
        defaults['team_id'] = self.id
        return values

    @api.onchange('use_leads', 'use_opportunities')
    def _onchange_use_leads_opportunities(self):
        if not self.use_leads and not self.use_opportunities:
            self.alias_name = False
        if not self.use_opportunities and self.use_leads:
            self.use_leads = False

    @api.onchange('team_type')
    def _onchange_team_type(self):
        if self.team_type == 'sales':
            self.use_opportunities = True
            self.use_leads = lambda self: self.user_has_groups('crm.group_use_lead')
            self.dashboard_graph_model = 'pipeline'
        else:
            self.use_opportunities = False
            self.use_leads = False
        return super(Team, self)._onchange_team_type()

    @api.constrains('dashboard_graph_model', 'use_opportunities')
    def _check_graph_model(self):
        if not self.use_opportunities and self.dashboard_graph_model == 'pipeline':
            raise ValidationError(_("Dashboard graph content cannot be Pipeline if the sales channel doesn't use it. (Pipeline is unchecked.)"))

    @api.model
    def create(self, vals):
        generate_alias_name = self.env['ir.values'].get_default('sales.config.settings', 'generate_sales_team_alias')
        if generate_alias_name and not vals.get('alias_name'):
            vals['alias_name'] = vals.get('name')
        return super(Team, self).create(vals)

    @api.multi
    def write(self, vals):
        result = super(Team, self).write(vals)
        if vals.get('use_leads') or vals.get('alias_defaults'):
            for team in self:
                team.alias_id.write(team.get_alias_values())
        return result

    #TODO JEM : refactor this stuff with xml action, proper customization,
    @api.model
    def action_your_pipeline(self):
        action = self.env.ref('crm.crm_lead_opportunities_tree_view').read()[0]
        user_team_id = self.env.user.sale_team_id.id
        if not user_team_id:
            user_team_id = self.search([], limit=1).id
            action['help'] = """<p class='oe_view_nocontent_create'>Click here to add new opportunities</p><p>
    Looks like you are not a member of a sales channel. You should add yourself
    as a member of one of the sales channel.
</p>"""
            if user_team_id:
                action['help'] += "<p>As you don't belong to any sales channel, Odoo opens the first one by default.</p>"

        action_context = safe_eval(action['context'], {'uid': self.env.uid})
        if user_team_id:
            action_context['default_team_id'] = user_team_id

        tree_view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        form_view_id = self.env.ref('crm.crm_case_form_view_oppor').id
        kanb_view_id = self.env.ref('crm.crm_case_kanban_view_leads').id
        action['views'] = [
                [kanb_view_id, 'kanban'],
                [tree_view_id, 'tree'],
                [form_view_id, 'form'],
                [False, 'graph'],
                [False, 'calendar'],
                [False, 'pivot']
            ]
        action['context'] = action_context
        return action

    def _compute_dashboard_button_name(self):
        opportunity_teams = self.filtered('use_opportunities')
        opportunity_teams.update({'dashboard_button_name': _("Pipeline")})
        super(Team, self - opportunity_teams)._compute_dashboard_button_name()

    def action_primary_channel_button(self):
        if self.use_opportunities:
            action = self.env.ref('crm.crm_case_form_view_salesteams_opportunity').read()[0]
            return action
        return super(Team, self).action_primary_channel_button()

    def _graph_get_dates(self, today):
        """ return a coherent start and end date for the dashboard graph according to the graph settings.
        """
        if self.dashboard_graph_model == 'pipeline':
            if self.dashboard_graph_group == 'month':
                start_date = today.replace(day=1)
            elif self.dashboard_graph_group == 'week':
                start_date = today - relativedelta(days=today.isocalendar()[2] - 1)
            else:
                start_date = today

            if self.dashboard_graph_period == 'week':
                end_date = today + relativedelta(weeks=1)
            elif self.dashboard_graph_period == 'year':
                end_date = today + relativedelta(years=1)
            else:
                end_date = today + relativedelta(months=1)

            # we take the end of the preceding month/week/day if we group by month/week/day
            # (to avoid having twice the same month/week/day from different years/month/week)
            if self.dashboard_graph_group == 'month':
                end_date = end_date.replace(day=1) - relativedelta(days=1)
            elif self.dashboard_graph_group == 'week':
                end_date -= relativedelta(days=end_date.isocalendar()[2])
            else:
                end_date -= relativedelta(days=1)

            return [start_date, end_date]
        return super(Team, self)._graph_get_dates(today)

    def _graph_date_column(self):
        if self.dashboard_graph_model == 'pipeline':
            return 'date_deadline'
        return super(Team, self)._graph_date_column()

    def _graph_y_query(self):
        if self.dashboard_graph_model == 'pipeline':
            return 'SUM(expected_revenue)'
        return super(Team, self)._graph_y_query()

    def _graph_sql_table(self):
        if self.dashboard_graph_model == 'pipeline':
            return 'crm_opportunity_report'
        return super(Team, self)._graph_sql_table()

    def _graph_title_and_key(self):
        if self.dashboard_graph_model == 'pipeline':
            return ['', _('Expected Revenue')] # no more title
        return super(Team, self)._graph_title_and_key()
