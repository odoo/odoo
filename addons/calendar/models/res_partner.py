# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    meeting_count = fields.Integer("# Meetings", compute='_compute_meeting_count')
    meeting_ids = fields.Many2many('calendar.event', 'calendar_event_res_partner_rel', 'res_partner_id',
                                   'calendar_event_id', string='Meetings', copy=False)

    calendar_last_notif_ack = fields.Datetime(
        'Last notification marked as read from base Calendar', default=fields.Datetime.now)

    def _compute_meeting_count(self):
        result = self._compute_meeting()
        for p in self:
            p.meeting_count = len(result.get(p.id, []))

    def _compute_meeting(self):
        if self.ids:
            # prefetch 'parent_id'
            all_partners = self.with_context(active_test=False).search_fetch(
                [('id', 'child_of', self.ids)], ['parent_id'],
            )

            query = self.env['calendar.event']._search([])  # ir.rules will be applied
            query_str, params = query.subselect()

            self.env.cr.execute(f"""
                SELECT res_partner_id, calendar_event_id, count(1)
                  FROM calendar_event_res_partner_rel
                 WHERE res_partner_id IN %s AND calendar_event_id IN {query_str}
              GROUP BY res_partner_id, calendar_event_id
            """, [tuple(all_partners.ids)] + params)

            meeting_data = self.env.cr.fetchall()

            # Create a dict {partner_id: event_ids} and fill with events linked to the partner
            meetings = {p.id: set() for p in all_partners}
            for m in meeting_data:
                meetings[m[0]].add(m[1])

            # Add the events linked to the children of the partner
            for p in all_partners:
                partner = p
                while partner:
                    if partner in self:
                        meetings[partner.id] |= meetings[p.id]
                    partner = partner.parent_id
            return {p.id: list(meetings[p.id]) for p in self}
        return {}

    def get_attendee_detail(self, meeting_ids):
        """ Return a list of dict of the given meetings with the attendees details
            Used by:
                - base_calendar.js : Many2ManyAttendee
                - calendar_model.js (calendar.CalendarModel)
        """
        attendees_details = []
        meetings = self.env['calendar.event'].browse(meeting_ids)
        for attendee in meetings.attendee_ids:
            if attendee.partner_id not in self:
                continue
            attendee_is_organizer = self.env.user == attendee.event_id.user_id and attendee.partner_id == self.env.user.partner_id
            attendees_details.append({
                'id': attendee.partner_id.id,
                'name': attendee.partner_id.display_name,
                'status': attendee.state,
                'event_id': attendee.event_id.id,
                'attendee_id': attendee.id,
                'is_alone': attendee.event_id.is_organizer_alone and attendee_is_organizer,
                # attendees data is sorted according to this key in JS.
                'is_organizer': 1 if attendee.partner_id == attendee.event_id.user_id.partner_id else 0,
            })
        return attendees_details

    @api.model
    def _set_calendar_last_notif_ack(self):
        partner = self.env['res.users'].browse(self.env.context.get('uid', self.env.uid)).partner_id
        partner.write({'calendar_last_notif_ack': datetime.now()})

    def schedule_meeting(self):
        self.ensure_one()
        partner_ids = self.ids
        partner_ids.append(self.env.user.partner_id.id)
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action['context'] = {
            'default_partner_ids': partner_ids,
        }
        action['domain'] = ['|', ('id', 'in', self._compute_meeting()[self.id]), ('partner_ids', 'in', self.ids)]
        return action
