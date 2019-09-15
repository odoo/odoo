# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Lead(models.Model):
    _inherit = 'crm.lead'

    visitor_sessions_count = fields.Integer('# Sessions', compute="_compute_visitor_sessions_count")

    @api.depends('visitor_ids.mail_channel_ids')
    def _compute_visitor_sessions_count(self):
        for lead in self:
            lead.visitor_sessions_count = len(lead.visitor_ids.mail_channel_ids)

    def action_redirect_to_livechat_sessions(self):
        visitors = self.visitor_ids
        action = self.env.ref('website_livechat.website_visitor_livechat_session_action').read()[0]
        action['domain'] = [('livechat_visitor_id', 'in', visitors.ids)]
        return action
