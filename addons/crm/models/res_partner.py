# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    team_id = fields.Many2one('crm.team', string='Sales Team')
    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='Opportunities', domain=[('type', '=', 'opportunity')])
    meeting_ids = fields.Many2many('calendar.event', 'calendar_event_res_partner_rel', 'res_partner_id', 'calendar_event_id', string='Meetings', copy=False)
    opportunity_count = fields.Integer("Opportunity", compute='_compute_opportunity_count')
    meeting_count = fields.Integer("# Meetings", compute='_compute_meeting_count')

    @api.model
    def default_get(self, fields):
        rec = super(Partner, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        if active_model == 'crm.lead':
            lead = self.env[active_model].browse(self.env.context.get('active_id')).exists()
            if lead:
                rec.update(
                    phone=lead.phone,
                    mobile=lead.mobile,
                    function=lead.function,
                    title=lead.title.id,
                    website=lead.website,
                    street=lead.street,
                    street2=lead.street2,
                    city=lead.city,
                    state_id=lead.state_id.id,
                    country_id=lead.country_id.id,
                    zip=lead.zip,
                )
        return rec

    def _compute_opportunity_count(self):
        if self.ids:
            lead_group_data = self.env['crm.lead'].read_group(
                [('partner_id.commercial_partner_id', 'in', self.ids)],
                ['partner_id'], ['partner_id']
            )
        else:
            lead_group_data = []
        partners = dict(
            (m['partner_id'][0], m['partner_id_count'])
            for m in lead_group_data)
        commercial_partners = {}
        for partner in self.browse(partners.keys()):
            commercial_partners.setdefault(partner.commercial_partner_id.id, 0)
            commercial_partners[partner.commercial_partner_id.id] += partners[partner.id]
        for partner in self:
            if partner.is_company:
                partner.opportunity_count = commercial_partners.get(partner.id, 0)
            else:
                partner.opportunity_count = partners.get(partner.id, 0)

    def _compute_meeting_count(self):
        if self.ids:
            self.env.cr.execute("""
                SELECT res_partner_id, calendar_event_id, count(1)
                  FROM calendar_event_res_partner_rel
                 WHERE res_partner_id IN %s
              GROUP BY res_partner_id, calendar_event_id
            """, [tuple(self.ids)])
            meeting_data = self.env.cr.fetchall()
            events = [row[1] for row in meeting_data]
            valid_events = self.env['calendar.event'].search([('id', 'in', events)])  # filter for ACLs
            meetings = dict((m[0], m[2]) for m in meeting_data if m[1] in valid_events.ids)
        else:
            meetings = dict()
        for partner in self:
            partner.meeting_count = meetings.get(partner.id, 0)

    def schedule_meeting(self):
        partner_ids = self.ids
        partner_ids.append(self.env.user.partner_id.id)
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        action['context'] = {
            'default_partner_ids': partner_ids,
        }
        return action
