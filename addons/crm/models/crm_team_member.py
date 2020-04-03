# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, exceptions, fields, models, _
from odoo.addons.crm.models.crm_lead import LEAD_ASSIGN_EVAL_CONTEXT
from odoo.tools import safe_eval


class Team(models.Model):
    _inherit = 'crm.team.member'

    # assignment
    assignment_domain = fields.Char('Assignment Domain', tracking=True)
    assignment_max = fields.Integer('Max Leads (last 30 days)')
    lead_month_count = fields.Integer(
        'Leads (30 days)', compute='_compute_lead_month_count',
        help='Lead assigned to this member those last 30 days')

    @api.depends('user_id', 'crm_team_id')
    def _compute_lead_month_count(self):
        for member in self:
            if member.user_id.id and member.crm_team_id.id:
                limit_date = fields.Datetime.now() - datetime.timedelta(days=30)
                domain = [('user_id', '=', member.user_id.id),
                          ('team_id', '=', member.crm_team_id.id),
                          ('date_open', '>=', limit_date)]
                member.lead_month_count = self.env['crm.lead'].search_count(domain)
            else:
                member.lead_month_count = 0

    @api.constrains('assignment_domain')
    def _constrains_assignment_domain(self):
        for member in self:
            try:
                domain = safe_eval.safe_eval(member.assignment_domain or '[]', LEAD_ASSIGN_EVAL_CONTEXT)
                self.env['crm.lead'].search(domain, limit=1)
            except Exception:
                raise exceptions.UserError(_('Team membership assign domain is incorrectly formatted'))
