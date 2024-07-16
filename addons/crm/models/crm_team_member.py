# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging

from ast import literal_eval

from odoo import api, exceptions, fields, models, _
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class TeamMember(models.Model):
    _inherit = 'crm.team.member'

    # assignment
    assignment_enabled = fields.Boolean(related="crm_team_id.assignment_enabled")
    assignment_domain = fields.Char('Assignment Domain', tracking=True)
    assignment_optout = fields.Boolean('Skip auto assignment')
    assignment_max = fields.Integer('Average Leads Capacity (on 30 days)', default=30)
    lead_day_count = fields.Integer(
        'Leads (last 24h)', compute='_compute_lead_day_count',
        help='Lead assigned to this member this last day (lost one excluded)')
    lead_month_count = fields.Integer(
        'Leads (30 days)', compute='_compute_lead_month_count',
        help='Lead assigned to this member those last 30 days')

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_day_count(self):
        day_date = fields.datetime.now() - datetime.timedelta(hours=24)
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
