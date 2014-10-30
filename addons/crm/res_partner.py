# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, api, fields, _

class res_partner(models.Model):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'
    @api.one
    @api.depends('opportunity_count')
    def _opportunity_count(self):
        # the user may not have access rights for opportunities
        try:
            for partner in self:
                partner.opportunity_count = len(partner.opportunity_ids)
        except:
            pass

    @api.one
    @api.depends('meeting_count')
    def _meeting_count(self):
        # the user may not have access rights for meetings
        try:
            for partner in self:
                partner.meeting_count = len(partner.meeting_ids)
        except:
            pass

    @api.one
    @api.depends('phonecall_count')
    def _phonecall_count(self):
        for partner in self:
            partner.phonecall_count = len(partner.phonecall_ids)

    team_id = fields.Many2one('crm.team', 'Sales Team')
    opportunity_ids = fields.One2many('crm.lead', 'partner_id',
       'Opportunities', domain=[('type', '=', 'opportunity')])
    meeting_ids = fields.Many2many('calendar.event', 'calendar_event_res_partner_rel','res_partner_id', 'calendar_event_id',
        'Meetings')
    phonecall_ids = fields.One2many('crm.phonecall', 'partner_id', string='Phonecalls')
    opportunity_count = fields.Integer(compute='_opportunity_count', string="Opportunity")
    meeting_count = fields.Integer(compute='_meeting_count', string="# Meetings")
    phonecall_count = fields.Integer(compute='_phonecall_count', string="Phonecalls")

    @api.multi
    def redirect_partner_form(self, partner_id):
        search_view = self.pool['ir.model.data'].get_object_reference(self._cr, self._uid, 'base', 'view_res_partner_filter')
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': int(partner_id),
            'view_id': False,
            'context': self._context,
            'type': 'ir.actions.act_window',
            'search_view_id': search_view and search_view[1] or False
        }
        return value

#TODO: Not checked
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

    @api.v8
    @api.multi
    def make_opportunity(self, opportunity_summary, planned_revenue=0.0, probability=0.0, partner_id=None):
        lead_obj = self.pool['crm.lead']
        tag_ids = self.pool['crm.lead.tag'].search(self._cr, self._uid, [])
        opportunity_ids = {}
        for partner in self:
            if not partner_id:
                partner_id = partner.id
            opportunity_id = partner.opportunity_ids.create({
                'name' : opportunity_summary,
                'planned_revenue' : planned_revenue,
                'probability' : probability,
                'partner_id' : partner_id,
                'tag_ids' : tag_ids and tag_ids[0].id or [],
                'type': 'opportunity'
            })
            opportunity_ids[partner_id] = opportunity_id.id
        return opportunity_ids

    @api.v7
    def schedule_meeting(self, cr, uid, ids, context=None):
        partner_ids = list(ids)
        partner_ids.append(self.pool.get('res.users').browse(cr, uid, uid).partner_id.id)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
        res['context'] = {
            'search_default_partner_ids': list(ids),
            'default_partner_ids': partner_ids,
        }
        return res

    @api.v8
    @api.multi
    def schedule_meeting(self):
        partner_ids = list(self._ids)
        partner_ids.append(self.pool['res.users'].browse(self._cr, self._uid, self._uid).partner_id.id)
        res = self.pool['ir.actions.act_window'].for_xml_id(self._cr, self._uid, 'calendar', 'action_calendar_event', context=self._context)
        res['context'] = {
            'search_default_partner_ids': list(self._ids),
            'default_partner_ids': partner_ids,
        }
        return res