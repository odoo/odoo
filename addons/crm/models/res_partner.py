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

    @api.multi
    def _compute_opportunity_count(self):
        result_list = self.env['crm.lead'].read_group(
            [
                ('type', '=', 'opportunity'),
                '|',
                ('partner_id.commercial_partner_id', 'in', self.ids),
                ('partner_id', 'in', self.ids),
            ],
            ["id"],
            ["partner_id"]
        )
        result_map = {}
        involved_partners = self.browse([result['partner_id'][0] for result in result_list], self._prefetch)
        for partner, result in zip(involved_partners, result_list):
            result_map.setdefault(partner.id, 0)
            result_map[partner.id] += result['partner_id_count']
            # Count opportunities of a company and all its contacts
            if partner != partner.commercial_partner_id:
                result_map.setdefault(partner.commercial_partner_id.id, 0)
                result_map[partner.commercial_partner_id.id] += result['partner_id_count']
        for partner in self:
            partner.opportunity_count = result_map.get(partner.id, 0)

    @api.multi
    def _compute_meeting_count(self):
        for partner in self:
            partner.meeting_count = len(partner.meeting_ids)

    @api.multi
    def schedule_meeting(self):
        partner_ids = self.ids
        partner_ids.append(self.env.user.partner_id.id)
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        action['context'] = {
            'default_partner_ids': partner_ids,
        }
        return action
