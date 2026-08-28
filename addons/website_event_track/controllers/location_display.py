from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from werkzeug.exceptions import NotFound

from odoo import fields, http, tools
from odoo.http import request


class EventTrackLocationDisplayController(http.Controller):

    def _get_event_time_data(self, event):
        now = fields.Datetime.now()
        event_tz = event.date_tz or 'UTC'
        event_zone = ZoneInfo(event_tz)
        local_now = now.replace(tzinfo=UTC).astimezone(event_zone)
        local_today = local_now.date()
        return {
            'now': now,
            'event_tz': event_tz,
            'local_now': local_now,
            'today_start': datetime.combine(local_today, time.min, tzinfo=event_zone).astimezone(UTC).replace(tzinfo=None),
            'tomorrow_start': datetime.combine(local_today + timedelta(days=1), time.min, tzinfo=event_zone).astimezone(UTC).replace(tzinfo=None),
        }

    def _get_location_display_schedule(self, event, location, time_data):
        track_domain = [
            ('date', '!=', False),
            ('date_end', '!=', False),
            ('event_id', '=', event.id),
            ('is_published', '=', True),
            ('location_id', '=', location.id),
        ]
        tracks = event.env['event.track'].search([
            *track_domain,
            ('date', '>=', time_data['today_start']),
        ], order='date, id')
        tracks_today = tracks.filtered(lambda track: track.date < time_data['tomorrow_start'])

        live_track = tracks_today.filtered(lambda track: track.date <= time_data['now'] < track.date_end)[:1]
        upcoming_track_count = int(event.location_display_upcoming_track_count)
        upcoming_tracks = tracks_today.filtered(lambda track: track.date > time_data['now'])[:upcoming_track_count]
        next_track = upcoming_tracks[:1] or tracks.filtered(lambda track: track.date > time_data['now'])[:1]

        live_status = 'none'
        if live_track:
            live_status = 'live'
        elif upcoming_tracks:
            live_status = 'gap'
        elif tracks_today:
            live_status = 'finished'

        return {
            'live_track': live_track,
            'live_status': live_status,
            'location_name': location.name if tracks else event.name,
            'next_track': next_track,
            'upcoming_tracks': upcoming_tracks,
        }

    def _format_track_time(self, track, tz):
        return request.env._(
            "%(start_time)s – %(end_time)s",
            start_time=tools.format_time(request.env, track.date, tz=tz, time_format='short'),
            end_time=tools.format_time(request.env, track.date_end, tz=tz, time_format='short'),
        )

    def _get_location_display_values(self, event_id, location_id):
        event = request.env['event.event'].search([
            ('id', '=', event_id),
            ('website_published', '=', True),
            ('website_track', '=', True),
            ('website_id', 'in', (request.env.website.id, False)),
        ], limit=1)
        if not event:
            raise NotFound()
        location = request.env['event.track.location'].sudo().search([('id', '=', location_id)], limit=1)
        if not location:
            raise NotFound()
        time_data = self._get_event_time_data(event)
        schedule = self._get_location_display_schedule(event, location, time_data)
        formatted_track_day_label = False
        if next_track := schedule['next_track']:
            track_day = next_track.date.replace(tzinfo=UTC).astimezone(time_data['local_now'].tzinfo).date()
            date_label = tools.format_date(request.env, track_day, date_format='EEE d MMM')
            formatted_track_day_label = (
                request.env._("Tomorrow · %(date_label)s", date_label=date_label)
                if track_day == time_data['local_now'].date() + timedelta(days=1)
                else date_label
            )
        background_image_url = (
            f'/web/image/event.event/{event.id}/location_display_background'
            if event.location_display_background
            else False
        )
        return {
            'event': event,
            'location_id': location.id,
            'location_name': schedule['location_name'],
            'location_display_background_url': background_image_url,
            'current_time_label': '%s %s' % (
                tools.format_time(request.env, time_data['now'], tz=time_data['event_tz'], time_format='short'),
                time_data['local_now'].tzname(),
            ),
            'formatted_track_day_label': formatted_track_day_label,
            'format_track_time': lambda track: self._format_track_time(track, time_data['event_tz']),
            **schedule,
        }

    @http.route('/event/<int:event_id>/location-display/<int:location_id>', type='http', auth='public', website=True, sitemap=False, readonly=True)
    def location_display(self, event_id, location_id):
        return request.render(
            'website_event_track.event_track_location_display',
            self._get_location_display_values(event_id, location_id),
            headers=[('Cache-Control', 'no-store')]
        )

    @http.route('/event/<int:event_id>/location-display/<int:location_id>/content', type='jsonrpc', auth='public', website=True, sitemap=False, readonly=True)
    def location_display_content(self, event_id, location_id):
        return request.env['ir.ui.view']._render_template(
            'website_event_track.event_track_location_display_content',
            self._get_location_display_values(event_id, location_id),
        )
