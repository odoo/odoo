# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError


class Team(models.Model):
    _name = 'crm.team'
    _inherit = ['mail.alias.mixin', 'crm.team']
    _description = 'Sales Team'
    use_opportunities = fields.Boolean('Manage a pipeline', default=True, help="Check this box to manage a presales process with opportunities.")
    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True, help="The email address associated with this channel. New emails received will automatically create new leads assigned to the channel.")    

    unassigned_leads_count = fields.Integer(
        compute='_compute_unassigned_leads_count',
        string='Unassigned Leads')
    opportunities_count = fields.Integer(
        compute='_compute_opportunities',
        string='Number of open opportunities')
    overdue_opportunities_count = fields.Integer(
        compute='_compute_overdue_opportunities',
        string='Number of overdue opportunities')
    opportunities_amount = fields.Integer(
        compute='_compute_opportunities',
        string='Opportunities Revenues')
    overdue_opportunities_amount = fields.Integer(
        compute='_compute_overdue_opportunities',
        string='Overdue Opportunities Revenues')

    # Since we are in a _inherits case, this is not an override
    # but a plain definition of a field
    # So we need to reset the property related of that field
    alias_user_id = fields.Many2one('res.users', related='alias_id.alias_user_id', inherited=True, domain=lambda self: [
        ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman_all_leads').id)])

    def _compute_unassigned_leads_count(self):
        leads_data = self.env['crm.lead'].read_group([
            ('team_id', 'in', self.ids),
            ('type', '=', 'lead'),
            ('user_id', '=', False),
        ], ['team_id'], ['team_id'])
        counts = {datum['team_id'][0]: datum['team_id_count'] for datum in leads_data}
        for team in self:
            team.unassigned_leads_count = counts.get(team.id, 0)

    def _compute_opportunities(self):
        opportunity_data = self.env['crm.lead'].search([
            ('team_id', 'in', self.ids),
            ('probability', '<', 100),
            ('type', '=', 'opportunity'),
        ]).read(['planned_revenue', 'team_id'])
        counts = {}
        amounts = {}
        for datum in opportunity_data:
            counts.setdefault(datum['team_id'][0], 0)
            amounts.setdefault(datum['team_id'][0], 0)
            counts[datum['team_id'][0]] += 1
            amounts[datum['team_id'][0]] += (datum.get('planned_revenue', 0))
        for team in self:
            team.opportunities_count = counts.get(team.id, 0)
            team.opportunities_amount = amounts.get(team.id, 0)

    def _compute_overdue_opportunities(self):
        opportunity_data = self.env['crm.lead'].read_group([
            ('team_id', 'in', self.ids),
            ('probability', '<', 100),
            ('type', '=', 'opportunity'),
            ('date_deadline', '<', fields.Date.to_string(fields.Datetime.now()))
        ], ['planned_revenue', 'team_id'], ['team_id'])
        counts = {datum['team_id'][0]: datum['team_id_count'] for datum in opportunity_data}
        amounts = {datum['team_id'][0]: (datum['planned_revenue']) for datum in opportunity_data}
        for team in self:
            team.overdue_opportunities_count = counts.get(team.id, 0)
            team.overdue_opportunities_amount = amounts.get(team.id, 0)
    
    @api.onchange('use_opportunities')
    def _onchange_opportunities(self):
        if not self.use_opportunities:
            self.alias_name = False

    def get_alias_model_name(self, vals):
        return 'crm.lead'

    def get_alias_values(self):
        has_group_use_lead = self.env.user.has_group('crm.group_use_lead')
        values = super(Team, self).get_alias_values()
        values['alias_defaults'] = defaults = safe_eval(self.alias_defaults or "{}")
        defaults['type'] = 'lead' if has_group_use_lead  else 'opportunity'
        defaults['team_id'] = self.id
        return values   

    def write(self, vals):
        result = super(Team, self).write(vals)
        if 'alias_defaults' in vals:
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
            action['help'] = _("""<p class='o_view_nocontent_smiling_face'>Add new opportunities</p><p>
    Looks like you are not a member of a Sales Team. You should add yourself
    as a member of one of the Sales Team.
</p>""")
            if user_team_id:
                action['help'] += "<p>As you don't belong to any Sales Team, Odoo opens the first one by default.</p>"

        action_context = safe_eval(action['context'], {'uid': self.env.uid})
        if user_team_id:
            action_context['default_team_id'] = user_team_id

        action['context'] = action_context
        return action

    def _compute_dashboard_button_name(self):
        super(Team,self)._compute_dashboard_button_name()
        team_with_pipelines = self.filtered(lambda el: el.use_opportunities)
        team_with_pipelines.update({'dashboard_button_name': _("Pipeline")})

    def action_primary_channel_button(self):
        if self.use_opportunities:
            return self.env.ref('crm.crm_case_form_view_salesteams_opportunity').read()[0]
        return super(Team,self).action_primary_channel_button()
    
    def _graph_get_model(self):
        if self.use_opportunities:
            return 'crm.lead'
        return super(Team,self)._graph_get_model()

    def _graph_date_column(self):
        if self.use_opportunities:
            return 'create_date'
        return super(Team,self)._graph_date_column()

    def _graph_y_query(self):
        if self.use_opportunities:
            return 'count(*)'
        return super(Team,self)._graph_y_query()

    def _extra_sql_conditions(self):
        if self.use_opportunities:
            return "AND type LIKE 'opportunity'"
        return super(Team,self)._extra_sql_conditions()

    def _graph_title_and_key(self):
        if self.use_opportunities:
            return ['', _('New Opportunities')] # no more title
        return super(Team,self)._graph_title_and_key()
