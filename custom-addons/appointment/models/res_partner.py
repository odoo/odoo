# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time

from odoo import models


class Partner(models.Model):
    _inherit = "res.partner"

    def calendar_verify_availability(self, date_start, date_end):
        """ Verify availability of the partner(s) between 2 datetimes on their calendar.
        We only verify events that are not linked to an appointment type with resources since
        someone could take multiple appointment for multiple resources. The availability of
        resources is managed separately by booking lines (see ``appointment.booking.line`` model)

        :param datetime date_start: beginning of slot boundary. Not timezoned UTC;
        :param datetime date_end: end of slot boundary. Not timezoned UTC;
        """
        all_events = self.env['calendar.event'].search(
            ['&',
             ('partner_ids', 'in', self.ids),
             '&', '&',
             ('show_as', '=', 'busy'),
             ('stop', '>', datetime.combine(date_start, time.min)),
             ('start', '<', datetime.combine(date_end, time.max)),
            ],
            order='start asc',
        )
        events_excluding_appointment_resource = all_events.filtered(lambda ev: ev.appointment_type_id.schedule_based_on != 'resources')
        for event in events_excluding_appointment_resource:
            if event.allday or (event.start < date_end and event.stop > date_start):
                if event.attendee_ids.filtered_domain(
                        [('state', '!=', 'declined'),
                         ('partner_id', 'in', self.ids)]
                    ):
                    return False

        return True

    def _get_calendar_events(self, start_datetime, end_datetime):
        """Get a mapping from partner id to attended events intersecting with the time interval.

        :return dict[int, <calendar.event>]:
        """
        events = self.env['calendar.event'].search([
            ('stop', '>=', start_datetime), ('start', '<=', end_datetime), ('partner_ids', 'in', self.ids)])

        event_by_partner_id = defaultdict(lambda: self.env['calendar.event'])
        for event in events:
            for partner in event.partner_ids:
                event_by_partner_id[partner.id] += event

        return dict(event_by_partner_id)
