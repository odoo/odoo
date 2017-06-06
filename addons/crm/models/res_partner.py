# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Partner(models.Model):

    _inherit = 'res.partner'

    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id')
    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='Opportunities', domain=[('type', '=', 'opportunity')])
    meeting_ids = fields.Many2many('calendar.event', 'calendar_event_res_partner_rel', 'res_partner_id', 'calendar_event_id', string='Meetings', copy=False)
    opportunity_count = fields.Integer("Opportunity", compute='_compute_opportunity_count')
    meeting_count = fields.Integer("# Meetings", compute='_compute_meeting_count')
    activities_count = fields.Integer("Activities", compute='_compute_activities_count')

    @api.multi
    def _compute_opportunity_count(self):
        for partner in self:
            operator = 'child_of' if partner.is_company else '='  # the opportunity count should counts the opportunities of this company and all its contacts
            partner.opportunity_count = self.env['crm.lead'].search_count([('partner_id', operator, partner.id), ('type', '=', 'opportunity')])

    @api.multi
    def _compute_meeting_count(self):
        for partner in self:
            partner.meeting_count = len(partner.meeting_ids)

    @api.multi
    def _compute_activities_count(self):
        activity_data = self.env['crm.activity.report'].read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        mapped_data = {act['partner_id'][0]: act['partner_id_count'] for act in activity_data}
        for partner in self:
            partner.activities_count = mapped_data.get(partner.id, 0)

    @api.multi
    def schedule_meeting(self):
        partner_ids = self.ids
        partner_ids.append(self.env.user.partner_id.id)
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        action['context'] = {
            'search_default_partner_ids': self._context['partner_name'],
            'default_partner_ids': partner_ids,
        }
        return action
