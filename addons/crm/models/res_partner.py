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

    @api.multi
    def redirect_partner_form(self, partner_id):
        self.ensure_one()
        search_view = self.env.ref('base.view_res_partner_filter')
        return {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': int(partner_id),
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
            'search_view_id': search_view.id or False
        }

    @api.multi
    def make_opportunity(self, opportunity_summary, planned_revenue=0.0, probability=0.0, partner_id=None):
        CrmLead = self.env['crm.lead']
        tag_ids = self.env['crm.lead.tag'].search([])
        opportunity_ids = {}
        for partner in self:
            if not partner_id:
                partner_id = partner.id
            opportunity = CrmLead.create({
                'name' : opportunity_summary,
                'planned_revenue' : planned_revenue,
                'probability' : probability,
                'partner_id' : partner_id,
                'tag_ids' : tag_ids and tag_ids[0] or [],
                'type': 'opportunity'
            })
            opportunity_ids[partner_id] = opportunity.id
        return opportunity_ids

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
