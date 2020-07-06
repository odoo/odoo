# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from pytz import timezone, utc

from odoo import api, fields, models
from odoo.addons.resource.models.resource import float_to_time
from odoo.osv import expression


class Event(models.Model):
    _name = 'event.event'
    _inherit = 'event.event'

    # live information
    is_ongoing = fields.Boolean(
        'Is Ongoing', compute='_compute_time_data', search='_search_is_ongoing',
        help="Whether event has begun")
    is_done = fields.Boolean(
        'Is Event Done', compute='_compute_time_data',
        help="Event is finished")
    start_remaining = fields.Integer(
        'Remaining before start', compute='_compute_time_data',
        help="Remaining time before event starts (hours)")
    hour_from = fields.Float('Opening hour', default=8.0)
    hour_to = fields.Float('End hour', default=18.0)
    is_in_opening_hours = fields.Boolean(
        'Within opening hours', compute='_compute_is_is_opening_hours')

    @api.depends('date_begin', 'date_end')
    def _compute_time_data(self):
        """ Compute start and remaining time. Do everything in UTC as we compute only
        time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for event in self:
            date_begin_utc = utc.localize(event.date_begin, is_dst=False)
            date_end_utc = utc.localize(event.date_end, is_dst=False)
            event.is_ongoing = date_begin_utc <= now_utc <= date_end_utc
            event.is_done = now_utc > date_end_utc
            if date_begin_utc >= now_utc:
                td = date_begin_utc - now_utc
                event.event_start_remaining = int(td.total_seconds() / 60)
            else:
                event.event_start_remaining = 0

    @api.depends('is_ongoing', 'hour_from', 'hour_to', 'date_begin', 'date_end')
    def _compute_is_is_opening_hours(self):
        """ Opening hours: hour_from and hour_to are given within event TZ or UTC.
        Now() must therefore be computed based on that TZ. """
        for event in self:
            if not event.is_ongoing:
                event.is_in_opening_hours = False
            elif not event.hour_from or not event.hour_to:
                event.is_in_opening_hours = True
            else:
                event_tz = timezone(event.date_tz)
                # localize now, begin and end datetimes in event tz
                dt_begin = event.date_begin.astimezone(event_tz)
                dt_end = event.date_end.astimezone(event_tz)
                now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
                now_tz = now_utc.astimezone(event_tz)

                # compute opening hours
                opening_from_tz = event_tz.localize(datetime.combine(now_tz.date(), float_to_time(event.hour_from)))
                opening_to_tz = event_tz.localize(datetime.combine(now_tz.date(), float_to_time(event.hour_to)))

                opening_from = max([dt_begin, opening_from_tz])
                opening_to = min([dt_end, opening_to_tz])

                event.is_in_opening_hours = opening_from <= now_tz < opening_to

    def _compute_is_participating(self):
        """ Override is_participating to improve heuristic that is now

          * public, no visitor: not participating as we have no information;
          * public and visitor: check visitor is linked to a registration. As
            visitors are merged on the top parent, current visitor check is
            sufficient event for successive visits;
          * logged, no visitor: check partner is linked to a registration. Do
            not check the email as it is not really secure;
          * logged ad visitor: check partner or visitor are linked to a
            registration;
        """
        current_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
        if self.env.user._is_public() and not current_visitor:
            self.is_participating = False
        elif self.env.user._is_public():
            participating = self.env['event.registration'].sudo().search([
                ('event_id', 'in', self.ids),
                ('visitor_id', '=', current_visitor.id),
            ]).event_id
            for event in self:
                event.is_participating = event in participating
        else:
            if current_visitor:
                domain = [
                    '|',
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ('visitor_id', '=', current_visitor.id)
                ]
            else:
                domain = [('partner_id', '=', self.env.user.partner_id.id)]
            participating = self.env['event.registration'].sudo().search(
                expression.AND([
                    domain,
                    [('event_id', 'in', self.ids)]
                ])
            ).event_id
            for event in self:
                event.is_participating = event in participating

    def _get_menu_entries(self):
        """ Force tracking on Introduction and Location template-pages """
        res = super(Event, self)._get_menu_entries()
        return [
            (item[0], item[1], item[2], True)
            for item in res
        ]
