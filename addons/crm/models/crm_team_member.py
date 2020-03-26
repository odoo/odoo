# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, exceptions, fields, models, _
from odoo.addons.crm.models.crm_lead import LEAD_ASSIGN_EVAL_CONTEXT
from odoo.tools import safe_eval


class Team(models.Model):
    _inherit = 'crm.team.member'

    # assignment
    team_user_domain = fields.Char('Domain', tracking=True)
    maximum_user_leads = fields.Integer('Leads Per Month')
    lead_month_count = fields.Integer(
        'Assigned Leads', compute='_compute_lead_month_count',
        help='Lead assigned to this member those last 30 days')

    def _compute_lead_month_count(self):
        for member in self:
            if member.id:
                limit_date = fields.Datetime.now() - datetime.timedelta(days=30)
                domain = [('user_id', '=', member.user_id.id),
                          ('team_id', '=', member.crm_team_id.id),
                          ('date_open', '>=', limit_date)]
                member.lead_month_count = self.env['crm.lead'].search_count(domain)
            else:
                member.lead_month_count = 0

    @api.constrains('team_user_domain')
    def _constrains_team_user_domain(self):
        for member in self:
            try:
                domain = safe_eval.safe_eval(member.team_user_domain or '[]', LEAD_ASSIGN_EVAL_CONTEXT)
                self.env['crm.lead'].search(domain, limit=1)
            except Exception:
                raise exceptions.UserError(_('Team membership assign domain is incorrectly formatted'))
