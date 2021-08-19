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
        if active_model == 'crm.lead' and len(self.env.context.get('active_ids', [])) <= 1:
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
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        opportunity_data = self.env['crm.lead'].read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            fields=['partner_id'], groupby=['partner_id']
        )

        self.opportunity_count = 0
        for group in opportunity_data:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.opportunity_count += group['partner_id_count']
                partner = partner.parent_id

    def _compute_meeting_count(self):
        result = self._compute_meeting()
        for p in self:
            p.meeting_count = len(result.get(p.id, []))

    def _compute_meeting(self):
        if self.ids:
            all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
            self.env.cr.execute("""
                SELECT res_partner_id, calendar_event_id, count(1)
                  FROM calendar_event_res_partner_rel
                 WHERE res_partner_id IN %s
              GROUP BY res_partner_id, calendar_event_id
            """, [tuple(all_partners.ids)])
            meeting_data = self.env.cr.fetchall()

            # Keep only valid meeting data based on record rules of events
            events = [row[1] for row in meeting_data]
            events = self.env['calendar.event'].search([('id', 'in', events)]).ids
            meeting_data = [m for m in meeting_data if m[1] in events]

            # Create a dict {partner_id: event_ids} and fill with events linked to the partner
            meetings = {p.id: set() for p in all_partners}
            for m in meeting_data:
                meetings[m[0]].add(m[1])

            # Add the events linked to the children of the partner
            all_partners.read(['parent_id'])
            for p in all_partners:
                partner = p
                while partner:
                    if partner in self:
                        meetings[partner.id] |= meetings[p.id]
                    partner = partner.parent_id
            return {p.id: list(meetings[p.id]) for p in self if p.id}
        return {}


    def schedule_meeting(self):
        self.ensure_one()
        partner_ids = self.ids
        partner_ids.append(self.env.user.partner_id.id)
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action['context'] = {
            'default_partner_ids': partner_ids,
            'default_attendee_ids': [(0, 0, {'partner_id': pid}) for pid in partner_ids],
        }
        action['domain'] = ['|', ('id', 'in', self._compute_meeting()[self.id]), ('partner_ids', 'in', self.ids)]
        return action

    def action_view_opportunity(self):
        '''
        This function returns an action that displays the opportunities from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        if self.is_company:
            action['domain'] = [('partner_id.commercial_partner_id.id', '=', self.id)]
        else:
            action['domain'] = [('partner_id.id', '=', self.id)]
        return action
