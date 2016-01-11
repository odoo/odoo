# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'

    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id')
    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='Opportunities', domain=[('type', '=', 'opportunity')])
    meeting_ids = fields.Many2many('calendar.event', 'calendar_event_res_partner_rel', 'res_partner_id', 'calendar_event_id', string='Meetings')
    opportunity_count = fields.Integer(compute='_compute_opportunity_meeting_count', string="Opportunity")
    meeting_count = fields.Integer(compute='_compute_opportunity_meeting_count', string="# Meetings")

    def _compute_opportunity_meeting_count(self):
        for partner in self:
            operator = 'child_of' if partner.is_company else '='
            partner.opportunity_count = self.env['crm.lead'].search_count([('partner_id', operator, partner.id), ('type', '=', 'opportunity'), ('probability', '<', '100')])
            partner.meeting_count = len(partner.meeting_ids)

    @api.multi
    def schedule_meeting(self):
        partner_ids = self.ids
        partner_ids.append(self.env.user.partner_id.id)
        result = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
        result['context'] = {
            'search_default_partner_ids': self.env.context.get('partner_name'),
            'default_partner_ids': partner_ids,
        }
        return result
