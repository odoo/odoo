# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import random
import threading

from ast import literal_eval

from odoo import api, exceptions, fields, models, _
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class Team(models.Model):
    _name = 'crm.team'
    _inherit = ['mail.alias.mixin', 'crm.team']
    _description = 'Sales Team'

    use_leads = fields.Boolean('Leads', help="Check this box to filter and qualify incoming requests as leads before converting them into opportunities and assigning them to a salesperson.")
    use_opportunities = fields.Boolean('Pipeline', default=True, help="Check this box to manage a presales process with opportunities.")
    alias_id = fields.Many2one(
        'mail.alias', string='Alias', ondelete="restrict", required=True,
        help="The email address associated with this channel. New emails received will automatically create new leads assigned to the channel.")
    # assignment
    assignment_enabled = fields.Boolean('Lead Assign', compute='_compute_assignment_enabled')
    assignment_auto_enabled = fields.Boolean('Auto Assignment', compute='_compute_assignment_enabled')
    assignment_optout = fields.Boolean('Skip auto assignment')
    assignment_max = fields.Integer(
        'Lead Capacity', compute='_compute_assignment_max',
        help='Monthly leads for all salesmen belonging to the team')
    assignment_domain = fields.Char(
        'Assignment Domain', tracking=True,
        help='Additional filter domain when fetching unassigned leads to allocate to the team.')
    # statistics about leads / opportunities / both
    lead_unassigned_count = fields.Integer(
        string='# Unassigned Leads', compute='_compute_lead_unassigned_count')
    lead_all_assigned_month_count = fields.Integer(
        string='# Leads/Opps assigned this month', compute='_compute_lead_all_assigned_month_count',
        help="Number of leads and opportunities assigned this last month.")
    opportunities_count = fields.Integer(
        string='# Opportunities', compute='_compute_opportunities_data')
    opportunities_amount = fields.Monetary(
        string='Opportunities Revenues', compute='_compute_opportunities_data')
    opportunities_overdue_count = fields.Integer(
        string='# Overdue Opportunities', compute='_compute_opportunities_overdue_data')
    opportunities_overdue_amount = fields.Monetary(
        string='Overdue Opportunities Revenues', compute='_compute_opportunities_overdue_data',)
    # alias: improve fields coming from _inherits, use inherited to avoid replacing them
    alias_user_id = fields.Many2one(
        'res.users', related='alias_id.alias_user_id', inherited=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman_all_leads').id)])

    @api.depends('crm_team_member_ids.assignment_max')
    def _compute_assignment_max(self):
        for team in self:
            team.assignment_max = sum(member.assignment_max for member in team.crm_team_member_ids)

    def _compute_assignment_enabled(self):
        assign_enabled = self.env['ir.config_parameter'].sudo().get_param('crm.lead.auto.assignment', False)
        auto_assign_enabled = False
        if assign_enabled:
            assign_cron = self.sudo().env.ref('crm.ir_cron_crm_lead_assign', raise_if_not_found=False)
            auto_assign_enabled = assign_cron.active if assign_cron else False
        self.assignment_enabled = assign_enabled
        self.assignment_auto_enabled = auto_assign_enabled

    def _compute_lead_unassigned_count(self):
        leads_data = self.env['crm.lead'].read_group([
            ('team_id', 'in', self.ids),
            ('type', '=', 'lead'),
            ('user_id', '=', False),
        ], ['team_id'], ['team_id'])
        counts = {datum['team_id'][0]: datum['team_id_count'] for datum in leads_data}
        for team in self:
            team.lead_unassigned_count = counts.get(team.id, 0)

    @api.depends('crm_team_member_ids.lead_month_count')
    def _compute_lead_all_assigned_month_count(self):
        for team in self:
            team.lead_all_assigned_month_count = sum(member.lead_month_count for member in team.crm_team_member_ids)

    def _compute_opportunities_data(self):
        opportunity_data = self.env['crm.lead'].read_group([
            ('team_id', 'in', self.ids),
            ('probability', '<', 100),
            ('type', '=', 'opportunity'),
        ], ['expected_revenue:sum', 'team_id'], ['team_id'])
        counts = {datum['team_id'][0]: datum['team_id_count'] for datum in opportunity_data}
        amounts = {datum['team_id'][0]: datum['expected_revenue'] for datum in opportunity_data}
        for team in self:
            team.opportunities_count = counts.get(team.id, 0)
            team.opportunities_amount = amounts.get(team.id, 0)

    def _compute_opportunities_overdue_data(self):
        opportunity_data = self.env['crm.lead'].read_group([
            ('team_id', 'in', self.ids),
            ('probability', '<', 100),
            ('type', '=', 'opportunity'),
            ('date_deadline', '<', fields.Date.to_string(fields.Datetime.now()))
        ], ['expected_revenue', 'team_id'], ['team_id'])
        counts = {datum['team_id'][0]: datum['team_id_count'] for datum in opportunity_data}
        amounts = {datum['team_id'][0]: (datum['expected_revenue']) for datum in opportunity_data}
        for team in self:
            team.opportunities_overdue_count = counts.get(team.id, 0)
            team.opportunities_overdue_amount = amounts.get(team.id, 0)

    @api.onchange('use_leads', 'use_opportunities')
    def _onchange_use_leads_opportunities(self):
        if not self.use_leads and not self.use_opportunities:
            self.alias_name = False

    @api.constrains('assignment_domain')
    def _constrains_assignment_domain(self):
        for team in self:
            try:
                domain = literal_eval(team.assignment_domain or '[]')
                if domain:
                    self.env['crm.lead'].search(domain, limit=1)
            except Exception:
                raise exceptions.ValidationError(_('Assignment domain for team %(team)s is incorrectly formatted', team=team.name))

    # ------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------

    def write(self, vals):
        result = super(Team, self).write(vals)
        if 'use_leads' in vals or 'use_opportunities' in vals:
            for team in self:
                alias_vals = team._alias_get_creation_values()
                team.write({
                    'alias_name': alias_vals.get('alias_name', team.alias_name),
                    'alias_defaults': alias_vals.get('alias_defaults'),
                })
        return result

    # ------------------------------------------------------------
    # MESSAGING
    # ------------------------------------------------------------

    def _alias_get_creation_values(self):
        values = super(Team, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('crm.lead').id
        if self.id:
            if not self.use_leads and not self.use_opportunities:
                values['alias_name'] = False
            values['alias_defaults'] = defaults = literal_eval(self.alias_defaults or "{}")
            has_group_use_lead = self.env.user.has_group('crm.group_use_lead')
            defaults['type'] = 'lead' if has_group_use_lead and self.use_leads else 'opportunity'
            defaults['team_id'] = self.id
        return values

    # ------------------------------------------------------------
    # LEAD ASSIGNMENT
    # ------------------------------------------------------------

    @api.model
    def _cron_assign_leads(self):
        """ Cron method assigning leads. Leads are allocated to all teams and
        assigned to their members. It is based on cron configuration to
        deduce parameters of assignment to perform. Purpose of cron is to assign
        leads to sales persons. Assigned workload is set to 2 times the workload
        those sales people should perform between two cron iterations. Giving
        more allows more flexibility in their organization. If their maximum
        capacity is reached assign process won't give more leads to those people.

        e.g. cron is active with interval_number 3, interval_type days. This
        means cron runs every 3 days. Cron will assign leads for 6 work days
        to salespersons each 3 days unless their maximum capacity is reached.

        If cron runs on an hour-based schedule minimum assignment performed is
        equivalent to 2 workdays. Max assignment performed is for 30 days as it
        is better to run more often than planning for more than one month.

        See ``CrmTeam.action_assign_leads()`` and its sub methods for more
        details about assign process.
        """
        assign_cron = self.sudo().env.ref('crm.ir_cron_crm_lead_assign', raise_if_not_found=False)
        work_days = 2
        if assign_cron and assign_cron.active:
            if assign_cron.interval_type == 'months':
                work_days = 30  # maximum one month of work
            elif assign_cron.interval_type == 'weeks':
                work_days = 2 * assign_cron.interval_number * 7
            elif assign_cron.interval_type == 'days':
                work_days = 2 * assign_cron.interval_number * 1
        work_days = 30 if work_days > 30 else work_days
        self.env['crm.team'].search([
            '&', '|', ('use_leads', '=', True), ('use_opportunities', '=', True),
            ('assignment_optout', '=', False)
        ])._action_assign_leads(work_days=work_days)
        return True

    def action_assign_leads(self, work_days=2, log=True):
        """ Manual (direct) leads assignment. This method both

          * assigns leads to teams given by self;
          * assigns leads to salespersons belonging to self;

        See sub methods for more details about assign process.

        :param int work_days: number of work days to consider when assigning leads
          to teams or salespersons. We consider that Member.assignment_max (or
          its equivalent on team model) targets 30 work days. We make a ratio
          between expected number of work days and maximum assignment for those
          30 days to know lead count to assign.

        :return action: a client notification giving some insights on assign
          process;
        """
        teams_data, members_data = self._action_assign_leads(work_days=work_days)

        # format result messages
        logs = self._action_assign_leads_logs(teams_data, members_data)
        html_message = '<br />'.join(logs)
        notif_message = ' '.join(logs)

        # log a note in case of manual assign (as this method will mainly be called
        # on singleton record set, do not bother doing a specific message per team)
        log_action = _("Lead Assignment requested by %(user_name)s", user_name=self.env.user.name)
        log_message = "<p>%s<br /><br />%s</p>" % (log_action, html_message)
        self._message_log_batch(bodies=dict((team.id, log_message) for team in self))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _("Leads Assigned"),
                'message': notif_message,
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            }
        }

    def _action_assign_leads(self, work_days=2):
        """ Private method for lead assignment. This method both

          * assigns leads to teams given by self;
          * assigns leads to salespersons belonging to self;

        See sub methods for more details about assign process.

        :param int work_days: see ``CrmTeam.action_assign_leads()``;

        :return teams_data, members_data: structure-based result of assignment
          process. For more details about data see ``CrmTeam._allocate_leads()``
          and ``CrmTeamMember._assign_and_convert_leads``;
        """
        if not self.env.user.has_group('sales_team.group_sale_manager') and not self.env.user.has_group('base.group_system'):
            raise exceptions.UserError(_('Lead/Opportunities automatic assignment is limited to managers or administrators'))

        _logger.info('### START Lead Assignment (%d teams, %d sales persons, %d work_days)' % (len(self), len(self.crm_team_member_ids), work_days))
        teams_data = self._allocate_leads(work_days=work_days)
        _logger.info('### Team repartition done. Starting salesmen assignment.')
        members_data = self.crm_team_member_ids._assign_and_convert_leads(work_days=work_days)
        _logger.info('### END Lead Assignment')
        return teams_data, members_data

    def _action_assign_leads_logs(self, teams_data, members_data):
        """ Tool method to prepare notification about assignment process result.

        :param teams_data: see ``CrmTeam._allocate_leads()``;
        :param members_data: see ``CrmTeamMember._assign_and_convert_leads()``;

        :return list: list of formatted logs, ready to be formatted into a nice
        plaintext or html message at caller's will
        """
        # extract some statistics
        assigned = sum(len(teams_data[team]['assigned']) + len(teams_data[team]['merged']) for team in self)
        duplicates = sum(len(teams_data[team]['duplicates']) for team in self)
        members = len(members_data)
        members_assigned = sum(len(member_data['assigned']) for member_data in members_data.values())

        # format user notification
        message_parts = []
        # 1- duplicates removal
        if duplicates:
            message_parts.append(_("%(duplicates)s duplicates leads have been merged.",
                                   duplicates=duplicates))

        # 2- nothing assigned at all
        if not assigned and not members_assigned:
            if len(self) == 1:
                if not self.assignment_max:
                    message_parts.append(
                        _("No allocated leads to %(team_name)s team because it has no capacity. Add capacity to its salespersons.",
                          team_name=self.name))
                else:
                    message_parts.append(
                        _("No allocated leads to %(team_name)s team and its salespersons because no unassigned lead matches its domain.",
                          team_name=self.name))
            else:
                message_parts.append(
                    _("No allocated leads to any team or salesperson. Check your Sales Teams and Salespersons configuration as well as unassigned leads."))

        # 3- team allocation
        if not assigned and members_assigned:
            if len(self) == 1:
                message_parts.append(
                    _("No new lead allocated to %(team_name)s team because no unassigned lead matches its domain.",
                      team_name=self.name))
            else:
                message_parts.append(_("No new lead allocated to the teams because no lead match their domains."))
        elif assigned:
            if len(self) == 1:
                message_parts.append(
                    _("%(assigned)s leads allocated to %(team_name)s team.",
                      assigned=assigned, team_name=self.name))
            else:
                message_parts.append(
                    _("%(assigned)s leads allocated among %(team_count)s teams.",
                      assigned=assigned, team_count=len(self)))

        # 4- salespersons assignment
        if not members_assigned and assigned:
            message_parts.append(
                _("No lead assigned to salespersons because no unassigned lead matches their domains."))
        elif members_assigned:
            message_parts.append(
                _("%(members_assigned)s leads assigned among %(member_count)s salespersons.",
                  members_assigned=members_assigned, member_count=members))

        return message_parts

    def _allocate_leads(self, work_days=2):
        """ Allocate leads to teams given by self. This method sets ``team_id``
        field on lead records that are unassigned (no team and no responsible).
        No salesperson is assigned in this process. Its purpose is simply to
        allocate leads within teams.

        Heuristic of this method is the following:

          * first we randomize all teams;
          * then for each team

            * find unassigned leads, aka leads being

              * without team, without user -> not assigned;
              * not in a won stage, and not having False/0 (lost) or 100 (won)
                probability) -> live leads;
              * if set, a delay after creation can be applied (see BUNDLE_HOURS_DELAY)
                parameter explanations here below;

            * keep only leads matching the team's assignment domain (empty means
              everything);
            * assign maximum BUNDLE_SIZE leads to the team, then move to the
              next team. This is done to ensure every team will have leads
              enough to fill its capacity based on its domain;
            * when setting a team on leads, leads belonging to the current batch
              are also merged. Purpose is to clean database and avoid assigning
              duplicates to same or different teams;

          * evaluate which teams still need to receive leads. This is based on
            team maximum capacity. We consider a team should receive twice its
            capacity as leads. That way members will receive leads and can pick
            some leads in team unassigned pool of leads;

        Note that leads are assigned in batch meaning a team could receive
        leads that could better fit another team. However this heuristics is
        based on hypothesis that team domains do not overlap. Indeed if a
        company has several teams they will probably target separate market
        segments: country-based, customer type or size, ... Having several
        teams using same assignment domain could lead to less fairness in
        assignment process but this should not be the target use case of this
        heuristic.

        Leads are allocated by batch. This can be configured using a config
        parameter (see here below). Batch size depends on cron frequency,
        lead pipeline size and members assignment maximum. Finding an optimal
        heuristic for this parameter is not easy as it depends on internal
        processes and organization. Higher batch size leads to better performances
        when running automatic assignment. It can also give unfair results
        if teams domain overlap or if pipeline is not big enough to fill all
        teams capacity.

        :config int crm.assignment.bundle: optional config parameter allowing
          to set size of lead batch (BUNDLE_SIZE) allocated to a team at each
          iteration (50 by default based on experience);
        :config int crm.assignment.delay: optional config parameter giving a
          delay before taking a lead into assignment process (BUNDLE_HOURS_DELAY)
          given in hours. Purpose if to allow other crons or automated actions
          to make their job. This option is mainly historic as its purpose was
          to let automated actions prepare leads and score before PLS was added
          into CRM. This is now not required anymore but still supported;

        :param int work_days: see ``CrmTeam.action_assign_leads()``;

        :return teams_data: dict() with each team assignment result:
          team: {
            'assigned': set of lead IDs directly assigned to the team (no
              duplicate or merged found);
            'merged': set of lead IDs merged and assigned to the team (main
              leads being results of merge process);
            'duplicates': set of lead IDs found as duplicates and merged into
              other leads. Those leads are unlinked during assign process and
              are already removed at return of this method;
          }, ...
        """
        if not work_days or work_days > 30:
            raise ValueError(
                _('Leads team allocation should be done for at least 1 or maximum 30 work days, not %s.', work_days)
            )
        # assignment_max is valid for "30 days" -> divide by requested work_days
        # to have number of leads to assign
        assign_ratio = work_days / 30.0

        BUNDLE_HOURS_DELAY = int(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.delay', default=0))
        BUNDLE_SIZE = int(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.bundle', default=50))
        max_create_dt = fields.Datetime.now() - datetime.timedelta(hours=BUNDLE_HOURS_DELAY)

        team_done = self.env['crm.team']
        remaining_teams = self.env['crm.team'].browse(random.sample(self.ids, k=len(self.ids)))

        # compute assign domain for each team before looping on them by bundle size
        teams_domain = dict(
            (team, literal_eval(team.assignment_domain or '[]'))
            for team in remaining_teams
        )
        # compute limit of leads to assign to each team: 2 times team capacity, based on given work_days
        teams_limit = dict(
            (team, 2 * team.assignment_max * assign_ratio)
            for team in remaining_teams
        )
        # assignment process data
        teams_data = dict.fromkeys(remaining_teams, False)
        for team in remaining_teams:
            teams_data[team] = dict(assigned=set(), merged=set(), duplicates=set())

        remaining_teams = remaining_teams.filtered('assignment_max')
        while remaining_teams:
            for team in remaining_teams:
                lead_domain = expression.AND([
                    teams_domain[team],
                    [('create_date', '<', max_create_dt)],
                    ['&', ('team_id', '=', False), ('user_id', '=', False)],
                    ['|', ('stage_id.is_won', '=', False), ('probability', 'not in', [False, 0])]
                ])
                # assign only to reach asked team limit
                remaining = teams_limit[team] - (len(teams_data[team]['assigned']) + len(teams_data[team]['merged']))
                lead_limit = min([BUNDLE_SIZE, remaining if remaining > 0 else 1])
                leads = self.env["crm.lead"].search(lead_domain, limit=lead_limit)

                # assign + deduplicate and concatenate results in teams_data to keep some history
                assign_res = team._allocate_leads_deduplicate(leads)
                _logger.info('Assigned %d leads among %d candidates to team %s' % (len(assign_res['assigned']) + len(assign_res['merged']), len(leads), team.id))
                _logger.info('\tLeads: direct assign %s / merge result %s / duplicates merged: %s' % (
                    assign_res['assigned'], assign_res['merged'], assign_res['duplicates']
                ))
                for key in ('assigned', 'merged', 'duplicates'):
                    teams_data[team][key].update(assign_res[key])

                # either no more lead matching domain, either asked capacity assigned
                if len(leads) < lead_limit or (len(teams_data[team]['assigned']) + len(teams_data[team]['merged'])) >= teams_limit[team]:
                    team_done += team

                # auto-commit except in testing mode. As this process may be time consuming or we
                # may encounter errors, already commit what is allocated to avoid endless cron loops.
                auto_commit = not getattr(threading.currentThread(), 'testing', False)
                if auto_commit:
                    self._cr.commit()

            remaining_team_ids = (remaining_teams - team_done).ids
            remaining_teams = self.env['crm.team'].browse(random.sample(remaining_team_ids, k=len(remaining_team_ids)))

        # some final log
        _logger.info('## Assigned %s leads' % sum(len(team_data['assigned']) + len(team_data['merged']) for team_data in teams_data.values()))

        return teams_data

    def _allocate_leads_deduplicate(self, leads):
        """ Assign leads to sales team given by self by calling lead tool
        method _handle_salesmen_assignment. In this method we deduplicate leads
        allowing to reduce number of resulting leads before assigning them
        to salesmen.

        :param leads: recordset of leads to assign to current team;
        """
        self.ensure_one()

        # classify leads
        leads_assigned = self.env['crm.lead']  # direct team assign
        leads_done_ids, leads_merged_ids, leads_dup_ids = set(), set(), set()  # classification
        leads_dups_dict = dict()  # lead -> its duplicate
        for lead in leads:
            if lead.id not in leads_done_ids:
                lead_duplicates = lead._get_lead_duplicates(email=lead.email_from)
                if len(lead_duplicates) > 1:
                    leads_dups_dict[lead] = lead_duplicates
                    leads_done_ids.update((lead + lead_duplicates).ids)
                else:
                    leads_assigned += lead
                    leads_done_ids.add(lead.id)

        leads_assigned._handle_salesmen_assignment(user_ids=None, team_id=self.id)

        for lead in leads.filtered(lambda lead: lead in leads_dups_dict):
            lead_duplicates = leads_dups_dict[lead]
            merged = lead_duplicates._merge_opportunity(user_id=False, team_id=self.id, max_length=0)
            leads_dup_ids.update((lead_duplicates - merged).ids)
            leads_merged_ids.add(merged.id)

            # auto-commit except in testing mode
            auto_commit = not getattr(threading.currentThread(), 'testing', False)
            if auto_commit:
                self._cr.commit()

        return {
            'assigned': set(leads_assigned.ids),
            'merged': leads_merged_ids,
            'duplicates': leads_dup_ids,
        }

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    #TODO JEM : refactor this stuff with xml action, proper customization,
    @api.model
    def action_your_pipeline(self):
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_action_pipeline")
        user_team_id = self.env.user.sale_team_id.id
        if user_team_id:
            # To ensure that the team is readable in multi company
            user_team_id = self.search([('id', '=', user_team_id)], limit=1).id
        else:
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
        super(Team, self)._compute_dashboard_button_name()
        team_with_pipelines = self.filtered(lambda el: el.use_opportunities)
        team_with_pipelines.update({'dashboard_button_name': _("Pipeline")})

    def action_primary_channel_button(self):
        if self.use_opportunities:
            return self.env["ir.actions.actions"]._for_xml_id("crm.crm_case_form_view_salesteams_opportunity")
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
        return super(Team, self)._graph_title_and_key()
