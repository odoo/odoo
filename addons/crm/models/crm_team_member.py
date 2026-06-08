# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging

from ast import literal_eval

from odoo import api, exceptions, fields, models, _
from odoo.tools import float_round

_logger = logging.getLogger(__name__)

MEMBER_MAX_LEAD_ASSIGNMENT_QUOTA = 30000  # Arbitrarily large - 1000 per day (math.inf causes issues on runbot)


class CrmTeamMember(models.Model):
    _inherit = 'crm.team.member'

    # assignment
    assignment_enabled = fields.Boolean(related="crm_team_id.assignment_enabled")
    assignment_domain = fields.Char('Assignment Domain', tracking=True)
    assignment_domain_preferred = fields.Char('Preference assignment Domain', tracking=True)
    assignment_max = fields.Integer('Average Leads Capacity (on 30 days)', default=MEMBER_MAX_LEAD_ASSIGNMENT_QUOTA)
    assignment_rules = fields.Selection([
        ('unlimited', 'Always in rotation'),
        ('limited', 'In rotation, with a limit'),
        ('opt-out', 'Out of rotation')
    ], string='Auto-Assignment Rules', compute='_compute_assignment_rules',
        store=False, readonly=False)
    lead_day_count = fields.Integer(
        'Leads (last 24h)', compute='_compute_lead_day_count',
        help='Number of leads assigned to this member in the last 24 hours (lost leads excluded)')
    lead_month_count = fields.Integer(
        'Leads (30 days)', compute='_compute_lead_month_count',
        help='Number of leads assigned to this member in the last 30 days')

    @api.depends('assignment_max')
    def _compute_assignment_rules(self):
        for member in self:
            if member.assignment_max >= MEMBER_MAX_LEAD_ASSIGNMENT_QUOTA:
                member.assignment_rules = 'unlimited'
            elif member.assignment_max == 0:
                member.assignment_rules = 'opt-out'
            else:
                member.assignment_rules = 'limited'

    @api.onchange('assignment_rules')
    def _onchange_assignment_rules(self):
        for member in self:
            if member.assignment_rules == 'unlimited':
                member.assignment_max = MEMBER_MAX_LEAD_ASSIGNMENT_QUOTA
            elif member.assignment_rules == 'opt-out':
                member.assignment_max = 0
            else:
                member.assignment_max = 30

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_day_count(self):
        day_date = fields.Datetime.now() - datetime.timedelta(hours=24)
        daily_leads_counts = self._get_lead_from_date(day_date)

        for member in self:
            member.lead_day_count = daily_leads_counts.get((member.user_id.id, member.crm_team_id.id), 0)

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_month_count(self):
        month_date = fields.Datetime.now() - datetime.timedelta(days=30)
        monthly_leads_counts = self._get_lead_from_date(month_date)

        for member in self:
            member.lead_month_count = monthly_leads_counts.get((member.user_id.id, member.crm_team_id.id), 0)

    def _get_lead_from_date(self, date_from, active_test=False):
        return {
            (user.id, team.id): count for user, team, count in self.env['crm.lead'].with_context(active_test=active_test)._read_group(
                [
                    ('date_open', '>=', date_from),
                    ('team_id', 'in', self.crm_team_id.ids),
                    ('user_id', 'in', self.user_id.ids),
                ],
                ['user_id', 'team_id'],
                ['__count'],
            )
        }

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

    @api.constrains('assignment_domain_preferred')
    def _constrains_assignment_domain_preferred(self):
        for member in self:
            try:
                domain = literal_eval(member.assignment_domain_preferred or '[]')
                if domain:
                    self.env['crm.lead'].search(domain, limit=1)
            except Exception:
                raise exceptions.ValidationError(_(
                    'Member preferred assignment domain for user %(user)s and team %(team)s is incorrectly formatted',
                    user=member.user_id.name, team=member.crm_team_id.name
                ))

    # ------------------------------------------------------------
    # LEAD ASSIGNMENT
    # ------------------------------------------------------------

    def _get_assignment_quota(self, force_quota=False):
        """ Return the remaining daily quota based
        on the assignment_max and the lead already assigned in the past 24h

        :param bool force_quota: see ``CrmTeam._action_assign_leads()``;
        """
        quota = float_round(self.assignment_max / 30.0, precision_digits=0, rounding_method='HALF-UP')
        if force_quota:
            return quota
        return quota - self.lead_day_count
