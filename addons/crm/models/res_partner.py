# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class ResPartner(models.Model):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'

    @api.multi
    def _compute_opportunity_meeting_phonecall_count(self):
        # the user may not have access rights for opportunities or meetings
        try:
            for partner in self:
                if partner.is_company:
                    operator = 'child_of'
                else:
                    operator = '='
                partner.opportunity_count = self.env['crm.lead'].search_count([('partner_id', operator, partner.id), ('lead_type', '=', 'opportunity'), ('probability', '<', '100')])
                partner.meeting_count = len(partner.meeting_ids)
        except:
            pass
        for partner in self:
            partner.phonecall_count = len(partner.phonecall_ids)

    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id')
    opportunity_ids = fields.One2many('crm.lead', 'partner_id',\
        string='Opportunities', domain=[('lead_type', '=', 'opportunity')])
    meeting_ids = fields.Many2many('calendar.event', 'calendar_event_res_partner_rel', 'res_partner_id', 'calendar_event_id', string='Meetings')
    phonecall_ids = fields.One2many('crm.phonecall', 'partner_id',\
        string='Phonecalls')
    opportunity_count = fields.Integer(compute='_compute_opportunity_meeting_phonecall_count', string="Opportunity")
    meeting_count = fields.Integer(compute='_compute_opportunity_meeting_phonecall_count', string="# Meetings")
    phonecall_count = fields.Integer(compute='_compute_opportunity_meeting_phonecall_count', string="Phonecalls")

    @api.multi
    def schedule_meeting(self):
        partner_ids = self.ids + self.env.user.partner_id.ids
        result = self.env['ir.actions.act_window'].for_xml_id(
            'calendar', 'action_calendar_event')
        result['context'] = {
            'search_default_partner_ids': self.ids,
            'default_partner_ids': partner_ids
        }
        return result
