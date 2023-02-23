# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import random
import threading

from ast import literal_eval

from odoo import api, exceptions, fields, models, _
from odoo.osv import expression
from odoo.tools import float_compare, float_round
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
        'Lead Average Capacity', compute='_compute_assignment_max',
        help='Monthly average leads capacity for all salesmen belonging to the team')
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
        'res.users', related='alias_id.alias_user_id', readonly=False, inherited=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman_all_leads').id)])
    # properties
    lead_properties_definition = fields.PropertiesDefinition('Lead Properties')

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
        leads_data = self.env['crm.lead']._read_group([
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
        opportunity_data = self.env['crm.lead']._read_group([
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
        opportunity_data = self.env['crm.lead']._read_group([
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

    def unlink(self):
        """ When unlinking, concatenate ``crm.lead.scoring.frequency`` linked to
        the team into "no team" statistics. """
        frequencies = self.env['crm.lead.scoring.frequency'].search([('team_id', 'in', self.ids)])
        if frequencies:
            existing_noteam = self.env['crm.lead.scoring.frequency'].sudo().search([
                ('team_id', '=', False),
                ('variable', 'in', frequencies.mapped('variable'))
            ])
            for frequency in frequencies:
                # skip void-like values
                if float_compare(frequency.won_count, 0.1, 2) != 1 and float_compare(frequency.lost_count, 0.1, 2) != 1:
                    continue

                match = existing_noteam.filtered(lambda frequ_nt: frequ_nt.variable == frequency.variable and frequ_nt.value == frequency.value)
                if match:
                    # remove extra .1 that may exist in db as those are artifacts of initializing
                    # frequency table. Final value of 0 will be set to 0.1.
                    exist_won_count = float_round(match.won_count, precision_digits=0, rounding_method='HALF-UP')
                    exist_lost_count = float_round(match.lost_count, precision_digits=0, rounding_method='HALF-UP')
                    add_won_count = float_round(frequency.won_count, precision_digits=0, rounding_method='HALF-UP')
                    add_lost_count = float_round(frequency.lost_count, precision_digits=0, rounding_method='HALF-UP')
                    new_won_count = exist_won_count + add_won_count
                    new_lost_count = exist_lost_count + add_lost_count
                    match.won_count = new_won_count if float_compare(new_won_count, 0.1, 2) == 1 else 0.1
                    match.lost_count = new_lost_count if float_compare(new_lost_count, 0.1, 2) == 1 else 0.1
                else:
                    existing_noteam += self.env['crm.lead.scoring.frequency'].sudo().create({
                        'lost_count': frequency.lost_count if float_compare(frequency.lost_count, 0.1, 2) == 1 else 0.1,
                        'team_id': False,
                        'value': frequency.value,
                        'variable': frequency.variable,
                        'won_count': frequency.won_count if float_compare(frequency.won_count, 0.1, 2) == 1 else 0.1,
                    })
        return super(Team, self).unlink()

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
    def _cron_assign_leads(self, work_days=None):
        """ Cron method assigning leads. Leads are allocated to all teams and
        assigned to their members. It is based on either cron configuration
        either forced through ``work_days`` parameter.

        When based on cron configuration purpose of cron is to assign leads to
        sales persons. Assigned workload is set to the workload those sales
        people should perform between two cron iterations. If their maximum
        capacity is reached assign process will not assign them any more lead.

        e.g. cron is active with interval_number 3, interval_type days. This
        means cron runs every 3 days. Cron will assign leads for 3 work days
        to salespersons each 3 days unless their maximum capacity is reached.

        If cron runs on an hour- or minute-based schedule minimum assignment
        performed is equivalent to 0.2 workdays to avoid rounding issues.
        Max assignment performed is for 30 days as it is better to run more
        often than planning for more than one month. Assign process is best
        designed to run every few hours (~4 times / day) or each few days.

        See ``CrmTeam.action_assign_leads()`` and its sub methods for more
        details about assign process.

        :param float work_days: see ``CrmTeam.action_assign_leads()``;
        """
        assign_cron = self.sudo().env.ref('crm.ir_cron_crm_lead_assign', raise_if_not_found=False)
        if not work_days and assign_cron and assign_cron.active:
            if assign_cron.interval_type == 'months':
                work_days = 30  # maximum one month of work
            elif assign_cron.interval_type == 'weeks':
                work_days = min(30, assign_cron.interval_number * 7)  # max at 30 (better lead repartition)
            elif assign_cron.interval_type == 'days':
                work_days = min(30, assign_cron.interval_number * 1)  # max at 30 (better lead repartition)
            elif assign_cron.interval_type == 'hours':
                work_days = max(0.2, assign_cron.interval_number / 24)    # min at 0.2 to avoid small numbers issues
            elif assign_cron.interval_type == 'minutes':
                work_days = max(0.2, assign_cron.interval_number / 1440)    # min at 0.2 to avoid small numbers issues
        work_days = work_days if work_days else 1  # avoid void values
        self.env['crm.team'].search([
            '&', '|', ('use_leads', '=', True), ('use_opportunities', '=', True),
            ('assignment_optout', '=', False)
        ])._action_assign_leads(work_days=work_days)
        return True

    def action_assign_leads(self, work_days=1, log=True):
        """ Manual (direct) leads assignment. This method both

          * assigns leads to teams given by self;
          * assigns leads to salespersons belonging to self;

        See sub methods for more details about assign process.

        :param float work_days: number of work days to consider when assigning leads
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

    def _action_assign_leads(self, work_days=1):
        """ Private method for lead assignment. This method both

          * assigns leads to teams given by self;
          * assigns leads to salespersons belonging to self;

        See sub methods for more details about assign process.

        :param float work_days: see ``CrmTeam.action_assign_leads()``;

        :return teams_data, members_data: structure-based result of assignment
          process. For more details about data see ``CrmTeam._allocate_leads()``
          and ``CrmTeamMember._assign_and_convert_leads``;
        """
        if not self.env.user.has_group('sales_team.group_sale_manager') and not self.env.user.has_group('base.group_system'):
            raise exceptions.UserError(_('Lead/Opportunities automatic assignment is limited to managers or administrators'))

        _logger.info('### START Lead Assignment (%d teams, %d sales persons, %.2f work_days)', len(self), len(self.crm_team_member_ids), work_days)
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
        assigned = sum(len(teams_data[team]['assigned']) + len(teams_data[team]['merged']) for team in teams_data)
        duplicates = sum(len(teams_data[team]['duplicates']) for team in teams_data)
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

    def _allocate_leads(self, work_days=1):
        """ Allocate leads to teams given by self. This method sets ``team_id``
        field on lead records that are unassigned (no team and no responsible).
        No salesperson is assigned in this process. Its purpose is simply to
        allocate leads within teams.

        This process allocates all available leads on teams weighted by their
        maximum assignment by month that indicates their relative workload.

        Heuristic of this method is the following:
          * find unassigned leads for each team, aka leads being
            * without team, without user -> not assigned;
            * not in a won stage, and not having False/0 (lost) or 100 (won)
              probability) -> live leads;
            * if set, a delay after creation can be applied (see BUNDLE_HOURS_DELAY)
              parameter explanations here below;
            * matching the team's assignment domain (empty means
              everything);

          * assign a weight to each team based on their assignment_max that
            indicates their relative workload;

          * pick a random team using a weighted random choice and find a lead
            to assign:

            * remove already assigned leads from the available leads. If there
              is not any lead spare to assign, remove team from active teams;
            * pick the first lead and set the current team;
            * when setting a team on leads, leads are also merged with their
              duplicates. Purpose is to clean database and avoid assigning
              duplicates to same or different teams;
            * add lead and its duplicates to already assigned leads;

          * pick another random team until their is no more leads to assign
            to any team;

        This process ensure that teams having overlapping domains will all
        receive leads as lead allocation is done one lead at a time. This
        allocation will be proportional to their size (assignment of their
        members).

        :config int crm.assignment.bundle: deprecated
        :config int crm.assignment.commit.bundle: optional config parameter allowing
          to set size of lead batch to be committed together. By default 100
          which is a good trade-off between transaction time and speed
        :config int crm.assignment.delay: optional config parameter giving a
          delay before taking a lead into assignment process (BUNDLE_HOURS_DELAY)
          given in hours. Purpose if to allow other crons or automated actions
          to make their job. This option is mainly historic as its purpose was
          to let automated actions prepare leads and score before PLS was added
          into CRM. This is now not required anymore but still supported;

        :param float work_days: see ``CrmTeam.action_assign_leads()``;

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
        if work_days < 0.2 or work_days > 30:
            raise ValueError(
                _('Leads team allocation should be done for at least 0.2 or maximum 30 work days, not %.2f.', work_days)
            )

        BUNDLE_HOURS_DELAY = int(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.delay', default=0))
        BUNDLE_COMMIT_SIZE = int(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.commit.bundle', 100))
        auto_commit = not getattr(threading.current_thread(), 'testing', False)

        # leads
        max_create_dt = self.env.cr.now() - datetime.timedelta(hours=BUNDLE_HOURS_DELAY)
        duplicates_lead_cache = dict()

        # teams data
        teams_data, population, weights = dict(), list(), list()
        for team in self:
            if not team.assignment_max:
                continue

            lead_domain = expression.AND([
                literal_eval(team.assignment_domain or '[]'),
                [('create_date', '<=', max_create_dt)],
                ['&', ('team_id', '=', False), ('user_id', '=', False)],
                ['|', ('stage_id', '=', False), ('stage_id.is_won', '=', False)]
            ])

            leads = self.env["crm.lead"].search(lead_domain)
            # Fill duplicate cache: search for duplicate lead before the assignation
            # avoid to flush during the search at every assignation
            for lead in leads:
                if lead not in duplicates_lead_cache:
                    duplicates_lead_cache[lead] = lead._get_lead_duplicates(email=lead.email_from)

            teams_data[team] = {
                "team": team,
                "leads": leads,
                "assigned": set(),
                "merged": set(),
                "duplicates": set(),
            }
            population.append(team)
            weights.append(team.assignment_max)

        # Start a new transaction, since data fetching take times
        # and the first commit occur at the end of the bundle,
        # the first transaction can be long which we want to avoid
        if auto_commit:
            self._cr.commit()

        # assignment process data
        global_data = dict(assigned=set(), merged=set(), duplicates=set())
        leads_done_ids, lead_unlink_ids, counter = set(), set(), 0
        while population:
            counter += 1
            team = random.choices(population, weights=weights, k=1)[0]

            # filter remaining leads, remove team if no more leads for it
            teams_data[team]["leads"] = teams_data[team]["leads"].filtered(lambda l: l.id not in leads_done_ids).exists()
            if not teams_data[team]["leads"]:
                population_index = population.index(team)
                population.pop(population_index)
                weights.pop(population_index)
                continue

            # assign + deduplicate and concatenate results in teams_data to keep some history
            candidate_lead = teams_data[team]["leads"][0]
            assign_res = team._allocate_leads_deduplicate(candidate_lead, duplicates_cache=duplicates_lead_cache)
            for key in ('assigned', 'merged', 'duplicates'):
                teams_data[team][key].update(assign_res[key])
                leads_done_ids.update(assign_res[key])
                global_data[key].update(assign_res[key])
            lead_unlink_ids.update(assign_res['duplicates'])

            # auto-commit except in testing mode. As this process may be time consuming or we
            # may encounter errors, already commit what is allocated to avoid endless cron loops.
            if auto_commit and counter % BUNDLE_COMMIT_SIZE == 0:
                # unlink duplicates once
                self.env['crm.lead'].browse(lead_unlink_ids).unlink()
                lead_unlink_ids = set()
                self._cr.commit()

        # unlink duplicates once
        self.env['crm.lead'].browse(lead_unlink_ids).unlink()

        if auto_commit:
            self._cr.commit()

        # some final log
        _logger.info('## Assigned %s leads', (len(global_data['assigned']) + len(global_data['merged'])))
        for team, team_data in teams_data.items():
            _logger.info(
                '## Assigned %s leads to team %s',
                len(team_data['assigned']) + len(team_data['merged']), team.id)
            _logger.info(
                '\tLeads: direct assign %s / merge result %s / duplicates merged: %s',
                team_data['assigned'], team_data['merged'], team_data['duplicates'])
        return teams_data

    def _allocate_leads_deduplicate(self, leads, duplicates_cache=None):
        """ Assign leads to sales team given by self by calling lead tool
        method _handle_salesmen_assignment. In this method we deduplicate leads
        allowing to reduce number of resulting leads before assigning them
        to salesmen.

        :param leads: recordset of leads to assign to current team;
        :param duplicates_cache: if given, avoid to perform a duplicate search
          and fetch information in it instead;
        """
        self.ensure_one()
        duplicates_cache = duplicates_cache if duplicates_cache is not None else dict()

        # classify leads
        leads_assigned = self.env['crm.lead']  # direct team assign
        leads_done_ids, leads_merged_ids, leads_dup_ids = set(), set(), set()  # classification
        leads_dups_dict = dict()  # lead -> its duplicate
        for lead in leads:
            if lead.id not in leads_done_ids:

                # fill cache if not already done
                if lead not in duplicates_cache:
                    duplicates_cache[lead] = lead._get_lead_duplicates(email=lead.email_from)
                lead_duplicates = duplicates_cache[lead].exists()

                if len(lead_duplicates) > 1:
                    leads_dups_dict[lead] = lead_duplicates
                    leads_done_ids.update((lead + lead_duplicates).ids)
                else:
                    leads_assigned += lead
                    leads_done_ids.add(lead.id)

        # assign team to direct assign (leads_assigned) + dups keys (to ensure their team
        # if they are elected master of merge process)
        dups_to_assign = [lead for lead in leads_dups_dict]
        leads_assigned.union(*dups_to_assign)._handle_salesmen_assignment(user_ids=None, team_id=self.id)

        for lead in leads.filtered(lambda lead: lead in leads_dups_dict):
            lead_duplicates = leads_dups_dict[lead]
            merged = lead_duplicates._merge_opportunity(user_id=False, team_id=False, auto_unlink=False, max_length=0)
            leads_dup_ids.update((lead_duplicates - merged).ids)
            leads_merged_ids.add(merged.id)

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
        return self._action_update_to_pipeline(action)

    @api.model
    def action_opportunity_forecast(self):
        action = self.env['ir.actions.actions']._for_xml_id('crm.crm_lead_action_forecast')
        return self._action_update_to_pipeline(action)

    @api.model
    def _action_update_to_pipeline(self, action):
        user_team_id = self.env.user.sale_team_id.id
        if user_team_id:
            # To ensure that the team is readable in multi company
            user_team_id = self.search([('id', '=', user_team_id)], limit=1).id
        else:
            user_team_id = self.search([], limit=1).id
            action['help'] = "<p class='o_view_nocontent_smiling_face'>%s</p><p>" % _("Create an Opportunity")
            if user_team_id:
                if self.user_has_groups('sales_team.group_sale_manager'):
                    action['help'] += "<p>%s</p>" % _("""As you are a member of no Sales Team, you are showed the Pipeline of the <b>first team by default.</b>
                                        To work with the CRM, you should <a name="%d" type="action" tabindex="-1">join a team.</a>""",
                                        self.env.ref('sales_team.crm_team_action_config').id)
                else:
                    action['help'] += "<p>%s</p>" % _("""As you are a member of no Sales Team, you are showed the Pipeline of the <b>first team by default.</b>
                                        To work with the CRM, you should join a team.""")
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
        self.ensure_one()
        if self.use_opportunities:
            action = self.env['ir.actions.actions']._for_xml_id('crm.crm_case_form_view_salesteams_opportunity')
            rcontext = {
                'team': self,
            }
            action['help'] = self.env['ir.ui.view']._render_template('crm.crm_action_helper', values=rcontext)
            return action
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
