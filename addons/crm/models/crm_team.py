# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import random
import threading

from ast import literal_eval
from markupsafe import Markup

from odoo import api, exceptions, fields, models, _
from odoo.osv import expression
from odoo.tools import float_compare, float_round, SQL
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class Team(models.Model):
    _name = 'crm.team'
    _inherit = ['mail.alias.mixin', 'crm.team']
    _description = 'Sales Team'

    use_leads = fields.Boolean('Leads', help="Check this box to filter and qualify incoming requests as leads before converting them into opportunities and assigning them to a salesperson.")
    use_opportunities = fields.Boolean('Pipeline', default=True, help="Check this box to manage a presales process with opportunities.")
    alias_id = fields.Many2one(help="The email address associated with this channel. New emails received will automatically create new leads assigned to the channel.")
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
    lead_all_assigned_month_exceeded = fields.Boolean('Exceed monthly lead assignement', compute="_compute_lead_all_assigned_month_count",
        help="True if the monthly lead assignment count is greater than the maximum assignment limit, false otherwise."
    )
    opportunities_count = fields.Integer(
        string='# Opportunities', compute='_compute_opportunities_data')
    opportunities_amount = fields.Monetary(
        string='Opportunities Revenues', compute='_compute_opportunities_data')
    opportunities_overdue_count = fields.Integer(
        string='# Overdue Opportunities', compute='_compute_opportunities_overdue_data')
    opportunities_overdue_amount = fields.Monetary(
        string='Overdue Opportunities Revenues', compute='_compute_opportunities_overdue_data',)
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
        ], ['team_id'], ['__count'])
        counts = {team.id: count for team, count in leads_data}
        for team in self:
            team.lead_unassigned_count = counts.get(team.id, 0)

    @api.depends('crm_team_member_ids.lead_month_count', 'assignment_max')
    def _compute_lead_all_assigned_month_count(self):
        for team in self:
            team.lead_all_assigned_month_count = sum(member.lead_month_count for member in team.crm_team_member_ids)
            team.lead_all_assigned_month_exceeded = team.lead_all_assigned_month_count > team.assignment_max

    def _compute_opportunities_data(self):
        opportunity_data = self.env['crm.lead']._read_group([
            ('team_id', 'in', self.ids),
            ('probability', '<', 100),
            ('type', '=', 'opportunity'),
        ], ['team_id'], ['__count', 'expected_revenue:sum'])
        counts_amounts = {team.id: (count, expected_revenue_sum) for team, count, expected_revenue_sum in opportunity_data}
        for team in self:
            team.opportunities_count, team.opportunities_amount = counts_amounts.get(team.id, (0, 0))

    def _compute_opportunities_overdue_data(self):
        opportunity_data = self.env['crm.lead']._read_group([
            ('team_id', 'in', self.ids),
            ('probability', '<', 100),
            ('type', '=', 'opportunity'),
            ('date_deadline', '<', fields.Date.to_string(fields.Datetime.now()))
        ], ['team_id'], ['__count', 'expected_revenue:sum'])
        counts_amounts = {team.id: (count, expected_revenue_sum) for team, count, expected_revenue_sum in opportunity_data}
        for team in self:
            team.opportunities_overdue_count, team.opportunities_overdue_amount = counts_amounts.get(team.id, (0, 0))

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
    def _cron_assign_leads(self, force_quota=False, creation_delta_days=7):
        """ Cron method assigning leads. Leads are allocated to all teams and
        assigned to their members.

        The cron is designed to run at least once a day or more.
        A number of leads will be assigned each time depending on the daily leads
        already assigned.
        This allows the assignation process based on the cron to work on a daily basis
        without allocating too much leads on members if the cron is executed multiple
        times a day.
        The daily quota of leads can be forcefully assigned with force_quota
        (ignoring the daily leads already assigned).

        See ``CrmTeam.action_assign_leads()`` and its sub methods for more
        details about assign process.

        """
        self.env['crm.team'].search([
            '&', '|', ('use_leads', '=', True), ('use_opportunities', '=', True),
            ('assignment_optout', '=', False)
        ])._action_assign_leads(force_quota=force_quota, creation_delta_days=creation_delta_days)
        return True

    def action_assign_leads(self):
        """ Manual (direct) leads assignment. This method both

          * assigns leads to teams given by self;
          * assigns leads to salespersons belonging to self;

        See sub methods for more details about assign process.

        :return action: a client notification giving some insights on assign
          process;
        """
        teams_data, members_data = self._action_assign_leads(force_quota=True)

        # format result messages
        logs = self._action_assign_leads_logs(teams_data, members_data)
        html_message = Markup('<br />').join(logs)
        notif_message = ' '.join(logs)

        # log a note in case of manual assign (as this method will mainly be called
        # on singleton record set, do not bother doing a specific message per team)
        log_action = _("Lead Assignment requested by %(user_name)s", user_name=self.env.user.name)
        log_message = Markup("<p>%s<br /><br />%s</p>") % (log_action, html_message)
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

    def _action_assign_leads(self, force_quota=False, creation_delta_days=7):
        """ Private method for lead assignment. This method both

          * assigns leads to teams given by self;
          * assigns leads to salespersons belonging to self;

        See sub methods for more details about assign process.

        :param bool force_quota: Assign the full daily quota without taking into account
                                 the leads already assigned today
        :param int creation_delta_days: Take into account all leads created in the last nb days (by default 7).
                                        If set to zero we take all the past leads.

        :return teams_data, members_data: structure-based result of assignment
          process. For more details about data see ``CrmTeam._allocate_leads()``
          and ``CrmTeam._assign_and_convert_leads``;
        """
        if not (self.env.user.has_group('sales_team.group_sale_manager') or self.env.is_system()):
            raise exceptions.UserError(_('Lead/Opportunities automatic assignment is limited to managers or administrators'))

        _logger.info(
            '### START Lead Assignment (%d teams, %d sales persons, force daily quota: %s)',
            len(self),
            len(self.crm_team_member_ids),
            "ON" if force_quota else "OFF")
        teams_data = self._allocate_leads(creation_delta_days=creation_delta_days)
        _logger.info('### Team repartition done. Starting salesmen assignment.')
        members_data = self._assign_and_convert_leads(force_quota=force_quota)
        _logger.info('### END Lead Assignment')
        return teams_data, members_data

    def _action_assign_leads_logs(self, teams_data, members_data):
        """ Tool method to prepare notification about assignment process result.

        :param teams_data: see ``CrmTeam._allocate_leads()``;
        :param members_data: see ``CrmTeam._assign_and_convert_leads()``;

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

    def _allocate_leads(self, creation_delta_days=7):
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
            * created in the last creation_delta_days (in the last week by default)
              This avoid to take into account old leads in the allocation.
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
        :config float crm.assignment.delay: optional config parameter giving a
          delay before taking a lead into assignment process (BUNDLE_HOURS_DELAY)
          given in hours. Purpose if to allow other crons or automation rules
          to make their job. This option is mainly historic as its purpose was
          to let automation rules prepare leads and score before PLS was added
          into CRM. This is now not required anymore but still supported;

        :param int creation_delta_days: see ``CrmTeam._action_assign_leads()``;

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

        BUNDLE_HOURS_DELAY = float(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.delay', default=0))
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
            if creation_delta_days > 0:
                lead_domain = expression.AND([
                    lead_domain,
                    [('create_date', '>', self.env.cr.now() - datetime.timedelta(days=creation_delta_days))]
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

    def _get_lead_to_assign_domain(self):
        return [
            ('user_id', '=', False),
            ('date_open', '=', False),
            ('team_id', 'in', self.ids),
        ]

    def _assign_and_convert_leads(self, force_quota=False):
        """ Main processing method to assign leads to sales team members. It also
        converts them into opportunities. This method should be called after
        ``_allocate_leads`` as this method assigns leads already allocated to
        the member's team. Its main purpose is therefore to distribute team
        workload on its members based on their capacity.

        This method follows the following heuristic
            * Get quota per member
            * Find all leads to be assigned per team
            * Sort list of members per number of leads received in the last 24h
            * Assign the lead using round robin
                * Find the first member with a compatible domain
                * Assign the lead
                * Move the member at the end of the list if quota is not reached
                * Remove it otherwise
                * Move to the next lead

        :param bool force_quota: see ``CrmTeam._action_assign_leads()``;

        :return members_data: dict() with each member assignment result:
          membership: {
            'assigned': set of lead IDs directly assigned to the member;
          }, ...

        """
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        result_data = {}
        commit_bundle_size = int(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.commit.bundle', 100))
        teams_with_members = self.filtered(lambda team: team.crm_team_member_ids)
        quota_per_member = {member: member._get_assignment_quota(force_quota=force_quota) for member in self.crm_team_member_ids}
        counter = 0
        leads_per_team = dict(self.env['crm.lead']._read_group(
            teams_with_members._get_lead_to_assign_domain(),
            ['team_id'],
            # Do not use recordset aggregation to avoid fetching all the leads at once in memory
            # We want to have in memory only leads for the current team
            # and make sure we need them before fetching them
            ['id:array_agg'],
        ))
        for team, leads_to_assign_ids in leads_per_team.items():
            members_to_assign = list(team.crm_team_member_ids.filtered(lambda member:
                not member.assignment_optout and quota_per_member.get(member, 0) > 0
            ).sorted(key=lambda member: quota_per_member.get(member, 0), reverse=True))
            if not members_to_assign:
                continue
            result_data.update({
                member: {"assigned": self.env["crm.lead"], "quota": quota_per_member[member]}
                for member in members_to_assign
            })
            # Need to check that record still exists since the ids have been fetched at the begining of the process
            # Previous iteration has commited the change, records may have been deleted in the meanwhile
            leads_to_assign = self.env['crm.lead'].browse(leads_to_assign_ids).exists()
            leads_per_member = {
                member: leads_to_assign.filtered_domain(literal_eval(member.assignment_domain or '[]'))
                for member in members_to_assign
            }
            for lead in leads_to_assign.sorted(lambda lead: (-lead.probability, id)):
                counter += 1
                member_found = next((member for member in members_to_assign if lead in leads_per_member[member]), False)
                if not member_found:
                    continue
                lead.with_context(mail_auto_subscribe_no_notify=True).convert_opportunity(
                    lead.partner_id,
                    user_ids=member_found.user_id.ids
                )
                result_data[member_found]['assigned'] += lead
                members_to_assign.remove(member_found)
                quota_per_member[member_found] -= 1
                if quota_per_member[member_found] > 0:
                    # If the member should receive more lead, send him back at the end of the list
                    members_to_assign.append(member_found)

                if auto_commit and counter % commit_bundle_size == 0:
                    self.env.cr.commit()
            # Make sure we commit at least at the end of the team
            if auto_commit:
                self.env.cr.commit()
            # Once we are done with a team we don't need to keep the leads in memory
            # Try to avoid to explode memory usage
            self.env.invalidate_all()

        _logger.info('Assigned %s leads to %s salesmen', sum(len(r['assigned']) for r in result_data.values()), len(result_data))
        for member, member_info in result_data.items():
            _logger.info('-> member %s of team %s: assigned %d/%d leads (%s)', member.id, member.crm_team_id.id, len(member_info["assigned"]), member_info["quota"], member_info["assigned"])
        return result_data

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
                if self.env.user.has_group('sales_team.group_sale_manager'):
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
            return SQL('create_date')
        return super(Team,self)._graph_date_column()

    def _graph_y_query(self):
        if self.use_opportunities:
            return SQL('count(*)')
        return super(Team,self)._graph_y_query()

    def _extra_sql_conditions(self):
        if self.use_opportunities:
            return SQL("type LIKE 'opportunity'")
        return super(Team,self)._extra_sql_conditions()

    def _graph_title_and_key(self):
        if self.use_opportunities:
            return ['', _('New Opportunities')] # no more title
        return super(Team, self)._graph_title_and_key()
