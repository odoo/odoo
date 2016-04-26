# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Partner(models.Model):

    _inherit = 'res.partner'

    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id')
    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='Opportunities', domain=[('type', '=', 'opportunity')])
    meeting_ids = fields.Many2many('calendar.event', 'calendar_event_res_partner_rel', 'res_partner_id', 'calendar_event_id', string='Meetings')
    opportunity_count = fields.Integer("Opportunity", compute='_compute_opportunity_count')
    meeting_count = fields.Integer("# Meetings", compute='_compute_meeting_count')
    activities_count = fields.Integer("Activities", compute='_compute_activities_count')

    @api.multi
    def _compute_opportunity_count(self):
        # TODO JEM : remove the try/except by putting a group on button
        try:
            for partner in self:
                operator = 'child_of' if partner.is_company else '='  # the opportunity count should counts the opportunities of this company and all its contacts
                partner.opportunity_count = self.env['crm.lead'].search_count([('partner_id', operator, partner.id), ('type', '=', 'opportunity')])
        except:
            pass

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

    # TODO JEM : it is still used ?
    @api.v7
    def redirect_partner_form(self, cr, uid, partner_id, context=None):
        search_view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'view_res_partner_filter')
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': int(partner_id),
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
            'search_view_id': search_view and search_view[1] or False
        }
        return value

    # TODO JEM : it is still used ?
    @api.v7
    def make_opportunity(self, cr, uid, ids, opportunity_summary, planned_revenue=0.0, probability=0.0, partner_id=None, context=None):
        lead_obj = self.pool.get('crm.lead')
        tag_ids = self.pool['crm.lead.tag'].search(cr, uid, [])
        opportunity_ids = {}
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = partner.id
            opportunity_id = lead_obj.create(cr, uid, {
                'name' : opportunity_summary,
                'planned_revenue' : planned_revenue,
                'probability' : probability,
                'partner_id' : partner_id,
                'tag_ids' : tag_ids and tag_ids[0] or [],
                'type': 'opportunity'
            }, context=context)
            opportunity_ids[partner_id] = opportunity_id
        return opportunity_ids

    @api.multi
    def schedule_meeting(self):
        partner_ids = self.ids
        partner_ids.append(self.env.user.partner_id.id)
        action = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
        action['context'] = {
            'search_default_partner_ids': self._context['partner_name'],
            'default_partner_ids': partner_ids,
        }
        return action
