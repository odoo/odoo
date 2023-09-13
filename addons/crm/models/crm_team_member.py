# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import threading
import random

from collections import defaultdict
from ast import literal_eval

from odoo import api, exceptions, fields, models, _

class TeamMember(models.Model):
    _inherit = 'crm.team.member'

    # assignment
    assignment_enabled = fields.Boolean(related="crm_team_id.assignment_enabled")
    assignment_domain = fields.Char('Assignment Domain', tracking=True)
    assignment_optout = fields.Boolean('Skip auto assignment')
    assignment_max = fields.Integer('Leads per Month', default=200)
    lead_month_count = fields.Integer(
        'Leads (30 days)', compute='_compute_lead_month_count',
        help='Lead assigned to this member those last 30 days')
    lead_day_count = fields.Integer(
        'Leads (1 day)', compute='_compute_lead_day_count',
        help='Lead assigned to this member over last 24 hours')

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_month_count(self):
        gd = self._compute_lead_count(30)
        for member in self:
            member.lead_month_count = gd.get((member.user_id.id, member.crm_team_id.id), 0)

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_day_count(self):
        gd = self._compute_lead_count(1)
        for member in self:
            member.lead_day_count = gd.get((member.user_id.id, member.crm_team_id.id), 0)

    def _compute_lead_count(self, days=30):
        limit_date = fields.Datetime.now() - datetime.timedelta(days=days)
        groups = self.env['crm.lead'].with_context(active_test=False)._read_group(
            [('date_open', '>=', limit_date), ('team_id', 'in', list(set(self.mapped('crm_team_id.id'))))],
            ['user_id', 'team_id'],
            ['__count']
        )
        return {(x[0].id, x[1].id): x[2] for x in groups}

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

    def _assign_and_convert_leads(self, work_days=1):
        """ Main processing method to assign leads to sales team members and
        converts them into opportunities. This method should be called after
        ``_allocate_leads`` as this method assigns leads already allocated to
        the member's team. Its main purpose is therefore to distribute team
        workload on its members based on their capacity.

        This method follows the following heuristic

          * assign based on remaining leads to assign this month
          * but no more than 5 days full of leads over one day

        :return { member_id: [leads.ids] }

        """
        members = self.filtered(lambda m: not m.assignment_optout and (m.assignment_max > m.lead_month_count))
        if not members:
            return False

        result = defaultdict(list)
        toassign = {m.id: m.assignment_max - m.lead_month_count for m in members}
        leads = self.env["crm.lead"].search([
                ('user_id', '=', False), ('date_open', '=', False),
                ('team_id', 'in', list(set(members.mapped('crm_team_id.id'))))
            ], order='probability DESC, id desc', limit=sum(toassign.values()))
        members_dom = {m.id: literal_eval(m.assignment_domain or '[]') for m in members}
        auto_commit = not getattr(threading.current_thread(), 'testing', False)

        for lead in leads:
            if sum(toassign.values()) < 1:
                break
            for member in random.choices(members, weights=toassign.values(), k=len(members)):
                if lead.team_id.id != member.crm_team_id.id:
                    continue
                if not lead.filtered_domain(members_dom[member.id]):
                    continue

                toassign[member.id] -= 1
                if len(result[member.id]) + member.lead_day_count > member.assignment_max // 6:
                    toassign[member.id] = 0
                result[member.id].append(lead.id)

                lead.with_context(mail_auto_subscribe_no_notify=True).convert_opportunity(
                    lead.partner_id,
                    user_ids=member.user_id.ids
                )
                if auto_commit and sum(toassign.values()) % 100 == 0:
                    self._cr.commit()
                break

        if auto_commit:
            self._cr.commit()
        print('*** ', result)
        return result
