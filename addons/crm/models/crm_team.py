# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError
from random import randint, shuffle
import datetime
import logging
import math

_logger = logging.getLogger(__name__)

evaluation_context = {
    'datetime': datetime,
    'context_today': datetime.datetime.now,
}


class CrmTeamMember(models.Model):
    _name = 'crm.team.member'
    _inherit = ['mail.thread']
    _description = 'Salesperson (Team Member)'

    team_id = fields.Many2one('crm.team', string='Sales Team', required=True)
    user_id = fields.Many2one('res.users', string='Saleman', required=True, domain=lambda self:
        [('groups_id', 'in', self.env.ref('base.group_user').ids), ('team_ids', 'not in', [self.env.context.get('default_team_id')])])
    name = fields.Char(string="Name", related='user_id.partner_id.display_name', readonly=False)
    email = fields.Char(string="Email", related='user_id.partner_id.email')
    phone = fields.Char(string="Phone", related='user_id.partner_id.phone')
    mobile = fields.Char(string="Mobile", related='user_id.partner_id.mobile')
    company_id = fields.Many2one(string="Company", related='user_id.partner_id.company_id')
    active = fields.Boolean(string='Running', default=True)
    team_member_domain = fields.Char('Domain', tracking=True)
    maximum_user_leads = fields.Integer('Leads Per Month')
    leads_count = fields.Integer('Assigned Leads', compute='_compute_count_leads', help='Assigned Leads this last month')
    percentage_leads = fields.Float(compute='_compute_percentage_leads', string='Percentage leads')

    def _compute_count_leads(self):
        for member in self:
            if member.id:
                limit_date = datetime.datetime.now() - datetime.timedelta(days=30)
                domain = [('user_id', '=', member.user_id.id),
                          ('team_id', '=', member.team_id.id),
                          ('assign_date', '>', fields.Datetime.to_string(limit_date))
                          ]
                member.leads_count = self.env['crm.lead'].search_count(domain)
            else:
                member.leads_count = 0

    def _compute_percentage_leads(self):
        for member in self:
            member.percentage_leads = round(100 * member.leads_count / float(member.maximum_user_leads), 2) if member.maximum_user_leads else 0.0

    @api.constrains('team_member_domain')
    def _assert_valid_domain(self):
        for member in self:
            try:
                domain = safe_eval(member.team_member_domain or '[]', evaluation_context)
                self.env['crm.lead'].search(domain, limit=1)
            except Exception:
                raise ValidationError('The domain is incorrectly formatted')


class Team(models.Model):
    _name = 'crm.team'
    _inherit = ['mail.alias.mixin', 'crm.team']
    _description = 'Sales Team'

    use_leads = fields.Boolean('Leads', help="Check this box to filter and qualify incoming requests as leads before converting them into opportunities and assigning them to a salesperson.")
    use_opportunities = fields.Boolean('Pipeline', default=True, help="Check this box to manage a presales process with opportunities.")
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
    team_domain = fields.Char('Domain', tracking=True)
    leads_count = fields.Integer(compute='_compute_leads_count')
    assigned_leads_count = fields.Integer(compute='_compute_assigned_leads_count')
    capacity = fields.Integer(compute='_compute_capacity')
    team_member_ids = fields.One2many('crm.team.member', 'team_id', string='Salesman')
    user_ids = fields.Many2many('res.users', string='Salesman User', compute='_compute_user_ids', store=True)

    @api.model
    @api.returns('self', lambda value: value.id if value else False)
    def _get_default_team_id(self, user_id=None, domain=None):
        if user_id is None:
            user_id = self.env.user.id
        team_id = self.sudo().search([('team_member_ids.user_id', '=', user_id)], limit=1)
        if not team_id:
            team_id = super(Team, self)._get_default_team_id(user_id=user_id, domain=domain)
        return team_id

    @api.constrains('team_domain')
    def _assert_valid_domain(self):
        for team in self:
            try:
                domain = safe_eval(team.team_domain or '[]', evaluation_context)
                self.env['crm.lead'].search(domain, limit=1)
            except Exception:
                raise ValidationError('The domain is incorrectly formatted')

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

    def _compute_leads_count(self):
        for team in self:
            if team.id:
                team.leads_count = self.env['crm.lead'].search_count([('team_id', '=', team.id)])
            else:
                team.leads_count = 0

    def _compute_assigned_leads_count(self):
        for team in self:
            limit_date = datetime.datetime.now() - datetime.timedelta(days=30)
            domain = [('assign_date', '>=', fields.Datetime.to_string(limit_date)),
                      ('team_id', '=', team.id),
                      ('user_id', '!=', False)
                      ]
            team.assigned_leads_count = self.env['crm.lead'].search_count(domain)

    def _compute_capacity(self):
        for team in self:
            team.capacity = sum(s.maximum_user_leads for s in team.team_member_ids)

    @api.depends('team_member_ids')
    def _compute_user_ids(self):
        for team in self:
            team.user_ids = team.team_member_ids.mapped('user_id')

    @api.onchange('use_leads', 'use_opportunities')
    def _onchange_use_leads_opportunities(self):
        if not self.use_leads and not self.use_opportunities:
            self.alias_name = False

    def get_alias_model_name(self, vals):
        return 'crm.lead'

    def get_alias_values(self):
        has_group_use_lead = self.env.user.has_group('crm.group_use_lead')
        values = super(Team, self).get_alias_values()
        values['alias_defaults'] = defaults = safe_eval(self.alias_defaults or "{}")
        defaults['type'] = 'lead' if has_group_use_lead and self.use_leads else 'opportunity'
        defaults['team_id'] = self.id
        return values

    def write(self, vals):
        result = super(Team, self).write(vals)
        if 'use_leads' in vals or 'alias_defaults' in vals:
            for team in self:
                team.alias_id.write(team.get_alias_values())
        return result

    #TODO JEM : refactor this stuff with xml action, proper customization,
    @api.model
    def action_your_pipeline(self):
        action = self.env.ref('crm.crm_lead_action_pipeline').read()[0]
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

    @api.model
    def direct_assign_leads(self, ids=[]):
        self._assign_leads()

    @api.model
    def assign_leads_to_salesteams(self, all_salesteams):
        BUNDLE_LEADS = 50
        shuffle(all_salesteams)
        haslead = True
        salesteams_done = []
        while haslead:
            haslead = False
            for salesteam in all_salesteams:
                if salesteam['id'] in salesteams_done:
                    continue
                domain = safe_eval(salesteam['team_domain'], evaluation_context)
                limit_date = fields.Datetime.to_string(datetime.datetime.now() - datetime.timedelta(hours=1))
                domain.extend([('create_date', '<', limit_date), ('team_id', '=', False), ('user_id', '=', False)])
                domain.extend(['|', ('stage_id.is_won', '=', False), '&', ('probability', '!=', 0), ('probability', '!=', 100)])
                leads = self.env["crm.lead"].search(domain, limit=BUNDLE_LEADS)
                haslead = haslead or (len(leads) == BUNDLE_LEADS)
                _logger.info('Assignation of %s leads for team %s' % (len(leads), salesteam['id']))
                _logger.debug('List of leads: %s' % leads)

                if len(leads) < BUNDLE_LEADS:
                    salesteams_done.append(salesteam['id'])

                leads.write({'team_id': salesteam['id']})

                # Erase fake/false email
                spams = [
                    x.id for x in leads
                    if x.email_from and not tools.email_normalize(x.email_from)
                ]

                if spams:
                    self.env["crm.lead"].browse(spams).write({'email_from': False})

                # Merge duplicated lead
                leads_done = set()
                leads_merged = set()

                for lead in leads:
                    if lead.id not in leads_done:
                        leads_duplicated = lead.get_duplicated_leads(False)
                        if len(leads_duplicated) > 1:
                            merged = leads_duplicated.with_context(assign_leads_to_salesteams=True).merge_opportunity(False, False)
                            _logger.debug('Lead [%s] merged of [%s]' % (merged, leads_duplicated))
                            leads_merged.add(merged.id)
                        leads_done.update(leads_duplicated.ids)
                    self._cr.commit()

    @api.model
    def assign_leads_to_salesmen(self, all_team_users):
        users = []
        for su in all_team_users:
            if (su.maximum_user_leads - su.leads_count) <= 0:
                continue
            domain = safe_eval(su.team_member_domain or '[]', evaluation_context)
            domain.extend([
                ('user_id', '=', False),
                ('assign_date', '=', False)
            ])

            # assignation rythm: 2 days of leads if a lot of leads should be assigned
            limit = int(math.ceil(su.maximum_user_leads / 15.0))

            domain.append(('team_id', '=', su.team_id.id))

            leads = self.env["crm.lead"].search(domain, limit=limit * len(su.team_id.team_member_ids))
            users.append({
                "su": su,
                "nbr": min(su.maximum_user_leads - su.leads_count, limit),
                "leads": leads
            })

        assigned = set()
        while users:
            i = 0

            # statistically select the user that should receive the next lead
            idx = randint(0, sum(u['nbr'] for u in users) - 1)

            while idx > users[i]['nbr']:
                idx -= users[i]['nbr']
                i += 1
            user = users[i]

            # Get the first unassigned leads available for this user
            while user['leads'] and user['leads'][0] in assigned:
                user['leads'] = user['leads'][1:]
            if not user['leads']:
                del users[i]
                continue

            # lead convert for this user
            lead = user['leads'][0]
            assigned.add(lead)

            # Assign date will be setted by write function
            data = {'user_id': user['su'].user_id.id}

            # ToDo in master/saas-14: add option mail_auto_subscribe_no_notify on the saleman/saleteam
            lead.with_context(mail_auto_subscribe_no_notify=True).write(data)
            lead.convert_opportunity(lead.partner_id and lead.partner_id.id or None)
            self._cr.commit()

            user['nbr'] -= 1
            if not user['nbr']:
                del users[i]

    @api.model
    def _assign_leads(self):
        _logger.info('### START leads assignation')

        all_salesteams = self.search_read(fields=['team_domain'], domain=[('team_domain', '!=', False)])

        all_team_users = self.env['crm.team.member'].search([])

        _logger.info('Start assign_leads_to_salesteams for %s teams' % len(all_salesteams))

        self.assign_leads_to_salesteams(all_salesteams)

        _logger.info('Start assign_leads_to_salesmen for %s salesmen' % len(all_team_users))

        self.assign_leads_to_salesmen(all_team_users)

        _logger.info('### END leads assignation')
