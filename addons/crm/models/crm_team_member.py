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


class TeamMember(models.Model):
    _inherit = 'crm.team.member'

    # assignment
    assignment_enabled = fields.Boolean(related="crm_team_id.assignment_enabled")
    assignment_domain = fields.Char('Assignment Domain', tracking=True)
    assignment_optout = fields.Boolean('Skip auto assignment')
    assignment_max = fields.Integer('Average Leads Capacity (on 30 days)', default=30)
    lead_month_count = fields.Integer(
        'Leads (30 days)', compute='_compute_lead_month_count',
        help='Lead assigned to this member those last 30 days')
    lead_day_count = fields.Integer(
        'Leads (last days)', compute='_compute_lead_day_count',
        help='Lead assigned to this member those last 30 days')

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_month_count(self):
        month_date = fields.Datetime.now() - datetime.timedelta(days=30)
        groups_30_days = self._get_lead_from_date(month_date)

        for member in self:
            key = (member.user_id.id, member.crm_team_id.id)
            member.lead_month_count = groups_30_days.get(key, 0)

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_day_count(self):
        day_date = fields.datetime.now() - datetime.timedelta(hours=24)
        groups_1_days = self._get_lead_from_date(day_date)

        for member in self:
            key = (member.user_id.id, member.crm_team_id.id)
            member.lead_day_count = groups_1_days.get(key, 0)

    def _get_lead_from_date(self, date_from):
        Lead = self.env['crm.lead'].with_context(active_test=False)
        return {(g[0].id, g[1].id): g[2] for g in Lead._read_group(
            [
                ('date_open', '>=', date_from),
                ('team_id', 'in', self.crm_team_id.ids),
                ('user_id', 'in', self.user_id.ids)
            ],
            ['user_id', 'team_id'],
            ['__count']
        )}

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

    # ------------------------------------------------------------
    # LEAD ASSIGNMENT
    # ------------------------------------------------------------

    def _assign_and_convert_leads(self, force_quota=False):
        """ Main processing method to assign leads to sales team members. It also
        converts them into opportunities. This method should be called after
        ``_allocate_leads`` as this method assigns leads already allocated to
        the member's team. Its main purpose is therefore to distribute team
        workload on its members based on their capacity.

        This method follows the following heuristic
            * split member per team
            * find all the lead to be assigned in the team
            * Sort member per lead receive in the last 24h
            * Assign the lead using round robin
                * Find the first member with a compatible domain
                * Assign the lead
                * Move the member at the end of the list if quota is not reach
                * Remove it otherwise

        :param bool force_quota: see ``CrmTeam._action_assign_leads()``;

        :return members_data: dict() with each member assignment result:
          membership: {
            'assigned': set of lead IDs directly assigned to the member;
          }, ...

        """
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        result_data = {}
        commit_bundle_size = int(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.commit.bundle', 100))
        counter = 0
        for team in self.crm_team_id:
            team_members = self.filtered(lambda member:
                member.crm_team_id == team and
                not member.assignment_optout and
                member.assignment_max > 0 and
                member._get_assignment_quota() > 0
            ).sorted("lead_day_count")
            if not team_members:
                continue
            quota_per_member = {member: member._get_assignment_quota(force_quota=force_quota) for member in team_members}
            result_data.update({member: {'assigned': self.env['crm.lead'], "quota": quota} for member, quota in quota_per_member.items()})
            members_dom = {m: literal_eval(m.assignment_domain or '[]') for m in team_members}
            leads = self.env["crm.lead"].search([
                    ('user_id', '=', False),
                    ('date_open', '=', False),
                    ('team_id', '=', team.id),
                    ('type', '=', 'lead'),
                ], order='probability DESC, id')
            for lead in leads:
                if not team_members:
                    break
                counter += 1
                for member in team_members:
                    if not lead.filtered_domain(members_dom[member]):
                        continue
                    lead.with_context(mail_auto_subscribe_no_notify=True).convert_opportunity(
                        lead.partner_id,
                        user_ids=member.user_id.ids
                    )
                    result_data[member]['assigned'] |= lead
                    team_members -= member
                    quota_per_member[member] -= 1
                    if quota_per_member[member] > 0:
                        # If the member should receive more lead, send him back at the end of the list
                        team_members |= member
                    break


                if auto_commit and counter % commit_bundle_size == 0:
                    self._cr.commit()

        if auto_commit:
            self._cr.commit()

        _logger.info('Assigned %s leads to %s salesmen', sum(len(r['assigned']) for r in result_data.values()), len(result_data))
        for member, member_info in result_data.items():
            _logger.info('-> member %s of team %s: assigned %d/%d leads (%s)', member.id, member.crm_team_id.id, len(member_info["assigned"]), member_info["quota"], member_info["assigned"])
        return result_data

    def _get_assignment_quota(self, force_quota=False):
        """ Return the remaining daily quota based
        on the assignment_max and the lead already assigned in the past 24h

        :param bool force_quota: see ``CrmTeam._action_assign_leads()``;
        """
        quota = round(self.assignment_max / 30.0)
        if force_quota:
            return quota
        return quota - self.lead_day_count
