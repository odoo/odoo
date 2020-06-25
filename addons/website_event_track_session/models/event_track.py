# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from pytz import utc

from odoo import api, fields, models


class EventTrack(models.Model):
    _inherit = "event.track"

    # Call to action
    website_cta = fields.Boolean('CTA Button')
    website_cta_title = fields.Char('CTA Title')
    website_cta_url = fields.Char('CTA Url')
    website_cta_delay = fields.Integer('CTA Delay')
    # time information for track
    is_track_live = fields.Boolean(
        'Is Track Live', compute='_compute_track_time_data',
        help="Track has started and is ongoing")
    is_track_soon = fields.Boolean(
        'Is Track Soon', compute='_compute_track_time_data',
        help="Track will begin soon")
    is_track_upcoming = fields.Boolean(
        'Is Track Upcoming', compute='_compute_track_time_data',
        help="Track is not yet started")
    is_track_done = fields.Boolean(
        'Is Track Done', compute='_compute_track_time_data',
        help="Track is finished")
    track_start_remaining = fields.Integer(
        'Minutes before track starts', compute='_compute_track_time_data',
        help="Remaining time before track starts (minutes)")
    track_start_relative = fields.Integer(
        'Minutes compare to track start', compute='_compute_track_time_data',
        help="Relative time compared to track start (minutes)")
    # time information for CTA
    is_website_cta_live = fields.Boolean(
        'Is CTA Live', compute='_compute_cta_time_data',
        help="CTA button is available")
    website_cta_start_remaining = fields.Integer(
        'Minutes before CTA starts', compute='_compute_cta_time_data',
        help="Remaining time before CTA starts (minutes)")

    @api.depends('date', 'date_end')
    def _compute_track_time_data(self):
        """ Compute start and remaining time for track itself. Do everything in
        UTC as we compute only time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for track in self:
            date_begin_utc = utc.localize(track.date, is_dst=False)
            date_end_utc = utc.localize(track.date_end, is_dst=False)
            track.is_track_live = date_begin_utc <= now_utc < date_end_utc
            track.is_track_soon = (date_begin_utc - now_utc).total_seconds() < 30*60 if date_begin_utc > now_utc else False
            track.is_track_upcoming = date_begin_utc > now_utc
            track.is_track_done = date_end_utc <= now_utc
            if date_begin_utc >= now_utc:
                track.track_start_relative = int((date_begin_utc - now_utc).total_seconds() / 60)
                track.track_start_remaining = track.track_start_relative
            else:
                track.track_start_relative = int((now_utc - date_begin_utc).total_seconds() / 60)
                track.track_start_remaining = 0

    @api.depends('date', 'date_end', 'website_cta', 'website_cta_delay')
    def _compute_cta_time_data(self):
        """ Compute start and remaining time for track itself. Do everything in
        UTC as we compute only time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for track in self:
            if not track.website_cta:
                track.is_cta_live = track.website_cta_start_remaining = False
                continue

            date_begin_utc = utc.localize(track.date, is_dst=False) + timedelta(minutes=track.website_cta_delay or 0)
            date_end_utc = utc.localize(track.date_end, is_dst=False)
            track.is_cta_live = date_begin_utc <= now_utc <= date_end_utc
            if date_begin_utc >= now_utc:
                td = date_begin_utc - now_utc
                track.website_cta_start_remaining = int(td.total_seconds() / 60)
            else:
                track.website_cta_start_remaining = 0
