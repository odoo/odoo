# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from random import randint
from pytz import utc

from odoo import api, fields, models
from odoo.osv import expression


class EventTrack(models.Model):
    _inherit = "event.track"

    # Call to action
    website_cta = fields.Boolean('Magic Button')
    website_cta_title = fields.Char('Button Title')
    website_cta_url = fields.Char('Button Target URL')
    website_cta_delay = fields.Integer('Button appears')
    # time information for track
    is_track_live = fields.Boolean(
        'Is Track Live', compute='_compute_track_time_data',
        help="Track has started and is ongoing")
    is_track_soon = fields.Boolean(
        'Is Track Soon', compute='_compute_track_time_data',
        help="Track begins soon")
    is_track_today = fields.Boolean(
        'Is Track Today', compute='_compute_track_time_data',
        help="Track begins today")
    is_track_upcoming = fields.Boolean(
        'Is Track Upcoming', compute='_compute_track_time_data',
        help="Track is not yet started")
    is_track_done = fields.Boolean(
        'Is Track Done', compute='_compute_track_time_data',
        help="Track is finished")
    track_start_remaining = fields.Integer(
        'Minutes before track starts', compute='_compute_track_time_data',
        help="Remaining time before track starts (seconds)")
    track_start_relative = fields.Integer(
        'Minutes compare to track start', compute='_compute_track_time_data',
        help="Relative time compared to track start (seconds)")
    # time information for CTA
    is_website_cta_live = fields.Boolean(
        'Is CTA Live', compute='_compute_cta_time_data',
        help="CTA button is available")
    website_cta_start_remaining = fields.Integer(
        'Minutes before CTA starts', compute='_compute_cta_time_data',
        help="Remaining time before CTA starts (seconds)")

    @api.depends('date', 'date_end')
    def _compute_track_time_data(self):
        """ Compute start and remaining time for track itself. Do everything in
        UTC as we compute only time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for track in self:
            if not track.date:
                track.is_track_live = track.is_track_soon = track.is_track_today = track.is_track_upcoming = track.is_track_done = False
                track.track_start_relative = track.track_start_remaining = 0
                continue
            date_begin_utc = utc.localize(track.date, is_dst=False)
            date_end_utc = utc.localize(track.date_end, is_dst=False)
            track.is_track_live = date_begin_utc <= now_utc < date_end_utc
            track.is_track_soon = (date_begin_utc - now_utc).total_seconds() < 30*60 if date_begin_utc > now_utc else False
            track.is_track_today = date_begin_utc.date() == now_utc.date()
            track.is_track_upcoming = date_begin_utc > now_utc
            track.is_track_done = date_end_utc <= now_utc
            if date_begin_utc >= now_utc:
                track.track_start_relative = int((date_begin_utc - now_utc).total_seconds())
                track.track_start_remaining = track.track_start_relative
            else:
                track.track_start_relative = int((now_utc - date_begin_utc).total_seconds())
                track.track_start_remaining = 0

    @api.depends('date', 'date_end', 'website_cta', 'website_cta_delay')
    def _compute_cta_time_data(self):
        """ Compute start and remaining time for track itself. Do everything in
        UTC as we compute only time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for track in self:
            if not track.website_cta:
                track.is_website_cta_live = track.website_cta_start_remaining = False
                continue

            date_begin_utc = utc.localize(track.date, is_dst=False) + timedelta(minutes=track.website_cta_delay or 0)
            date_end_utc = utc.localize(track.date_end, is_dst=False)
            track.is_website_cta_live = date_begin_utc <= now_utc <= date_end_utc
            if date_begin_utc >= now_utc:
                td = date_begin_utc - now_utc
                track.website_cta_start_remaining = int(td.total_seconds())
            else:
                track.website_cta_start_remaining = 0

    def _get_track_suggestions(self, restrict_domain=None, limit=None):
        """ Returns the next tracks suggested after going to the current one
        given by self. Tracks always belong to the same event.

        Heuristic is

          * live first;
          * then ordered by start date, finished being sent to the end;
          * wishlisted (manually or by default);
          * tag matching with current track;
          * location matching with current track;
          * finally a random to have an "equivalent wave" randomly given;

        :param restrict_domain: an additional domain to restrict candidates;
        :param limit: number of tracks to return;
        """
        self.ensure_one()

        base_domain = [
            '&',
            ('event_id', '=', self.event_id.id),
            ('id', '!=', self.id),
        ]
        if restrict_domain:
            base_domain = expression.AND([
                base_domain,
                restrict_domain
            ])

        track_candidates = self.search(base_domain, limit=None, order='date asc')
        if not track_candidates:
            return track_candidates

        track_candidates = track_candidates.sorted(
            lambda track:
                (track.is_published,
                 track.is_track_live,
                 track.track_start_remaining > 0,
                 -1 * track.track_start_remaining,
                 track.is_reminder_on,
                 not track.wishlisted_by_default,
                 len(track.tag_ids & self.tag_ids),
                 track.location_id == self.location_id,
                 randint(0, 20),
                ), reverse=True
        )

        return track_candidates[:limit]

    def get_backend_menu_id(self):
        return self.env.ref('event.event_main_menu').id
