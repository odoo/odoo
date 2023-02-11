# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import math
import threading
import random

from ast import literal_eval

from odoo import api, exceptions, fields, models, _
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class Team(models.Model):
    _inherit = 'crm.team.member'

    # assignment
    assignment_enabled = fields.Boolean(related="crm_team_id.assignment_enabled")
    assignment_domain = fields.Char('Assignment Domain', tracking=True)
    assignment_optout = fields.Boolean('Skip auto assignment')
    assignment_max = fields.Integer('Average Leads Capacity (on 30 days)', default=30)
    lead_month_count = fields.Integer(
        'Leads (30 days)', compute='_compute_lead_month_count',
        help='Lead assigned to this member those last 30 days')

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_month_count(self):
        for member in self:
            if member.user_id.id and member.crm_team_id.id:
                member.lead_month_count = self.env['crm.lead'].with_context(active_test=False).search_count(
                    member._get_lead_month_domain()
                )
            else:
                member.lead_month_count = 0

    @api.constrains('assignment_domain')
    def _constrains_assignment_domain(self):
        for member in self:
            try:
                domain = literal_eval(member.assignment_domain or '[]')
                if domain:
                    self.env['crm.lead'].search(domain, limit=1)
            except Exception:
                raise exceptions.ValidationError(_(
                    'Member assignment domain for user %(user)s and team %(team)s is incorrectly formatted',
                    user=member.user_id.name, team=member.crm_team_id.name
                ))

    def _get_lead_month_domain(self):
        limit_date = fields.Datetime.now() - datetime.timedelta(days=30)
        return [
            ('user_id', '=', self.user_id.id),
            ('team_id', '=', self.crm_team_id.id),
            ('date_open', '>=', limit_date),
        ]

    # ------------------------------------------------------------
    # LEAD ASSIGNMENT
    # ------------------------------------------------------------

    def _assign_and_convert_leads(self, work_days=1):
        """ Main processing method to assign leads to sales team members. It also
        converts them into opportunities. This method should be called after
        ``_allocate_leads`` as this method assigns leads already allocated to
        the member's team. Its main purpose is therefore to distribute team
        workload on its members based on their capacity.

        Preparation

          * prepare lead domain for each member. It is done using a logical
            AND with team's domain and member's domain. Member domains further
            restricts team domain;
          * prepare a set of available leads for each member by searching for
            leads matching domain with a sufficient limit to ensure all members
            will receive leads;
          * prepare a weighted population sample. Population are members that
            should received leads. Initial weight is the number of leads to
            assign to that specific member. This is minimum value between
            * remaining this month: assignment_max - number of lead already
              assigned this month;
            * days-based assignment: assignment_max with a ratio based on
              ``work_days`` parameter (see ``CrmTeam.action_assign_leads()``)
            * e.g. Michel Poilvache (max: 30 - currently assigned: 15) limit
              for 2 work days: min(30-15, 30/15) -> 2 leads assigned
            * e.g. Michel Tartopoil (max: 30 - currently assigned: 26) limit
              for 10 work days: min(30-26, 30/3) -> 4 leads assigned

        This method then follows the following heuristic

          * take a weighted random choice in population;
          * find first available (not yet assigned) lead in its lead set;
          * if found:
            * convert it into an opportunity and assign member as salesperson;
            * lessen member's weight so that other members have an higher
              probability of being picked up next;
          * if not found: consider this member is out of assignment process,
            remove it from population so that it is not picked up anymore;

        Assignment is performed one lead at a time for fairness purpose. Indeed
        members may have overlapping domains within a given team. To ensure
        some fairness in process once a member receives a lead, a new choice is
        performed with updated weights. This is not optimal from performance
        point of view but increases probability leads are correctly distributed
        within the team.

        :param float work_days: see ``CrmTeam.action_assign_leads()``;

        :return members_data: dict() with each member assignment result:
          membership: {
            'assigned': set of lead IDs directly assigned to the member;
          }, ...

        """
        if work_days < 0.2 or work_days > 30:
            raise ValueError(
                _('Leads team allocation should be done for at least 0.2 or maximum 30 work days, not %.2f.', work_days)
            )

        members_data, population, weights = dict(), list(), list()
        members = self.filtered(lambda member: not member.assignment_optout and member.assignment_max > 0)
        if not members:
            return members_data

        # prepare a global lead count based on total leads to assign to salespersons
        lead_limit = sum(
            member._get_assignment_quota(work_days=work_days)
            for member in members
        )

        # could probably be optimized
        for member in members:
            lead_domain = expression.AND([
                literal_eval(member.assignment_domain or '[]'),
                ['&', '&', ('user_id', '=', False), ('date_open', '=', False), ('team_id', '=', member.crm_team_id.id)]
            ])

            leads = self.env["crm.lead"].search(lead_domain, order='probability DESC', limit=lead_limit)

            to_assign = member._get_assignment_quota(work_days=work_days)
            members_data[member.id] = {
                "team_member": member,
                "max": member.assignment_max,
                "to_assign": to_assign,
                "leads": leads,
                "assigned": self.env["crm.lead"],
            }
            population.append(member.id)
            weights.append(to_assign)

        leads_done_ids = set()
        counter = 0
        # auto-commit except in testing mode
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        commit_bundle_size = int(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.commit.bundle', 100))
        while population:
            counter += 1
            member_id = random.choices(population, weights=weights, k=1)[0]
            member_index = population.index(member_id)
            member_data = members_data[member_id]

            lead = next((lead for lead in member_data['leads'] if lead.id not in leads_done_ids), False)
            if lead:
                leads_done_ids.add(lead.id)
                members_data[member_id]["assigned"] += lead
                weights[member_index] = weights[member_index] - 1

                lead.with_context(mail_auto_subscribe_no_notify=True).convert_opportunity(
                    lead.partner_id.id,
                    user_ids=member_data['team_member'].user_id.ids
                )

                if auto_commit and counter % commit_bundle_size == 0:
                    self._cr.commit()
            else:
                weights[member_index] = 0

            if weights[member_index] <= 0:
                population.pop(member_index)
                weights.pop(member_index)

            # failsafe
            if counter > 100000:
                population = list()

        if auto_commit:
            self._cr.commit()
        # log results and return
        result_data = dict(
            (member_info["team_member"], {"assigned": member_info["assigned"]})
            for member_id, member_info in members_data.items()
        )
        _logger.info('Assigned %s leads to %s salesmen', len(leads_done_ids), len(members))
        for member, member_info in result_data.items():
            _logger.info('-> member %s: assigned %d leads (%s)', member.id, len(member_info["assigned"]), member_info["assigned"])
        return result_data

    def _get_assignment_quota(self, work_days=1):
        """ Compute assignment quota based on work_days. This quota includes
        a compensation to speedup getting to the lead average (``assignment_max``).
        As this field is a counter for "30 days" -> divide by requested work
        days in order to have base assign number then add compensation.

        :param float work_days: see ``CrmTeam.action_assign_leads()``;
        """
        assign_ratio = work_days / 30.0
        to_assign = self.assignment_max * assign_ratio
        compensation = max(0, self.assignment_max - (self.lead_month_count + to_assign)) * 0.2
        return round(to_assign + compensation)
