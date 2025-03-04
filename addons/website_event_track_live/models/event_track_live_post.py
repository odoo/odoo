import requests
import logging
import base64

from datetime import datetime, timedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class EventTrackLivePost(models.Model):
    _name = 'event.track.live.post'
    _description = 'Event Track Live Post'

    event_track_id = fields.Many2one('event.track', 'Event Track Live', readonly=True)
    account_id = fields.Many2one('event.track.live.account', 'YouTube Account', required=True)
    name = fields.Char('Title', readonly=True)
    description = fields.Text('Description', readonly=True)
    thumbnail = fields.Image('YouTube Thumbnail', related='event_track_id.website_image', readonly=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('scheduled', 'Scheduled'),
        ('posted', 'Posted'),
        ('failed', 'Failed')], default='draft')

    company_id = fields.Many2one(related='event_track_id.company_id')

    youtube_video_id = fields.Char('YouTube Video ID', readonly=True)
    youtube_broadcast_id = fields.Char("YouTube Broadcast ID", help="The ID of the created YouTube live broadcast.", readonly=True)
    youtube_stream_id = fields.Char("YouTube Stream ID", help="The ID of the created YouTube live stream.", readonly=True)
    youtube_video_privacy = fields.Selection([
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
        ('private', 'Private')], default='unlisted', required=True, readonly=True)

    post_method = fields.Selection([
        ('now', 'Send now'),
        ('scheduled', 'Schedule later')], string="When", default='now', required=True)

    youtube_video_url = fields.Char('YouTube Video Link', compute='_compute_youtube_video_url', store=True)
    youtube_live_start_time = fields.Datetime('Scheduled Start Time', readonly=True)
    youtube_live_duration = fields.Float('YouTube Live Duration', readonly=True)

    failure_reason = fields.Text('Failure Reason', readonly=True)
    scheduled_date = fields.Datetime('Scheduled Date', readonly=True)

    @api.depends('youtube_video_id', 'youtube_video_url', 'state')
    def _compute_youtube_video_url(self):
        for post in self:
            if post.youtube_video_id:
                post.youtube_video_url = "https://www.youtube.com/watch?v=%s" % post.youtube_video_id

    def action_retry_post(self):
        self._action_post_youtube_live()

    def action_schedule_live_track(self):
        for track in self:
            track.write({'state': 'scheduled'})

    def action_post_live_track(self):
        for track in self:
            track.write({
                'post_method': 'now',
                'scheduled_date': False
            })

            track._action_post_youtube_live()

    def _action_post_youtube_live(self):
        self.ensure_one()
        if self.event_track_id.youtube_video_id:
            return

        self.account_id._refresh_youtube_token()
        self.state = 'ready'

        self._schedule_live()
        if self.state == 'failed':
            return False

        self._post_live_youtube()
        if self.state == 'failed':
            return False

        self._post_track_youtube_set_thumbnail()

    def _schedule_live(self):
        self.ensure_one()

        self.youtube_broadcast_id = self.youtube_broadcast_id or self._post_youtube_insert_broadcast()
        if not self.youtube_broadcast_id:
            return
        self.youtube_stream_id = self.youtube_stream_id or self._post_youtube_insert_livestream()
        if not self.youtube_stream_id:
            return

        bind_url = "https://www.googleapis.com/youtube/v3/liveBroadcasts/bind"
        result = requests.post(
            bind_url,
            params={
                'access_token': self.account_id.youtube_access_token,
                'part': 'id,contentDetails',
                'id': self.youtube_broadcast_id,
                'streamId': self.youtube_stream_id
            }
        )

        if not result.ok:
            values = self._parse_live_error_values('[Schedule]', result)
            self.write(values)

            _logger.warning("Failed to Bind YouTube Broadcast to YouTube Stream: %s", values['failure_reason'])
            return

        _logger.info("Youtube Broadcast '%s' was successfully bound to Stream '%s'.",
            self.youtube_broadcast_id,
            self.youtube_stream_id)
        self.youtube_video_id = self.youtube_broadcast_id

    def _post_youtube_insert_broadcast(self):
        self.ensure_one()

        broadcast_url = "https://www.googleapis.com/youtube/v3/liveBroadcasts"
        start, end = self._get_youtube_live_time()

        result = requests.post(
            broadcast_url,
            params={
                'access_token': self.account_id.youtube_access_token,
                'part': 'snippet,status,contentDetails'
            },
            json={
                "snippet": {
                    "title": self.name or "Live Broadcast",
                    "description": self.description or "",
                    "scheduledStartTime": start.isoformat() + "Z",
                    "scheduledEndTime": (end.isoformat() + "Z") if end else None,
                },
                "status": {
                    "privacyStatus": "private",
                    "selfDeclaredMadeForKids": False
                },
                "contentDetails": {
                    "recordFromStart": True,
                    "enableAutoStart": True,
                }
            }
        )
        if not result.ok:
            values = self._parse_live_error_values('[Broadcast]', result)
            self.write(values)

            _logger.warning("Failed to create YouTube Live Broadcast: %s", values['failure_reason'])
            return False

        broadcast_data = result.json()
        _logger.info(
            "Youtube Broadcast '%s' with title '%s' was published at '%s'.",
            broadcast_data['id'],
            broadcast_data['snippet']['title'],
            broadcast_data['snippet']['publishedAt']
        )
        return broadcast_data['id']

    def _post_youtube_insert_livestream(self):
        self.ensure_one()

        stream_url = "https://www.googleapis.com/youtube/v3/liveStreams"

        result = requests.post(
            stream_url,
            params={
                'access_token': self.account_id.youtube_access_token,
                'part': 'snippet,cdn'
            },
            json={
                "snippet": {
                    "title": self.name or "Live Stream",
                    "description": self.description or "",
                },
                "cdn": {
                    "resolution": "variable",  # Options: "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p"
                    "frameRate": "variable",
                    "ingestionType": "rtmp"
                }
            }
        )

        if not result.ok:
            values = self._parse_live_error_values('[Livestream]', result)
            self.write(values)

            _logger.warning("Failed to create YouTube Live Stream: %s", values['failure_reason'])
            return False

        stream_data = result.json()
        _logger.info(
            "Youtube Stream '%s' with title '%s' was inserted.",
            stream_data['id'],
            stream_data['snippet']['title'],
        )
        return stream_data['id']

    def _post_live_youtube(self):
        self.ensure_one()

        start, end = self._get_youtube_live_time()
        video_endpoint_url = "https://www.googleapis.com/youtube/v3/liveBroadcasts"
        result = requests.put(video_endpoint_url,
            params={
                'access_token': self.account_id.youtube_access_token,
                'part': 'snippet,status',
            },
            json={
                'id': self.youtube_broadcast_id,
                'snippet': {
                    'title': self.name,
                    "scheduledStartTime": start.isoformat() + "Z",
                    "scheduledEndTime": (end.isoformat() + "Z") if end else None,
                    'description': self.description,
                },
                'status': {
                    'privacyStatus': self.youtube_video_privacy,
                }
            },
            timeout=5
        )

        if not result.ok:
            values = self._parse_live_error_values('[Post]', result)
            self.write(values)
            return

        values = {
            'state': 'posted',
            'failure_reason': False
        }

        self.write(values)

    def _post_track_youtube_set_thumbnail(self):
        self.ensure_one()
        if not self.youtube_video_id or not self.thumbnail:
            return False

        # 50 units
        video_thumbnail_endpoint_url = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
        decoded_thumbnail = base64.b64decode(self.thumbnail)
        result = requests.post(video_thumbnail_endpoint_url,
            params={
                'access_token': self.account_id.youtube_access_token,
                'videoId': self.youtube_video_id,
            },
            data=decoded_thumbnail
        )

        if result.ok:
            values = {
                'state': 'posted',
                'failure_reason': False
            }
        else:
            values = self._parse_live_error_values('[Thumbnail]', result)
            values['state'] = 'posted'  # YouTube post succeed, only the thumbnail is failing

            _logger.warning("Failed to set YouTube thumbnail for video ID %s: %s", self.youtube_video_id, values['failure_reason'])

        return values

    def _get_youtube_live_time(self):
        start = max(self.youtube_live_start_time or datetime.now(), datetime.now())
        end = None
        if duration := self.youtube_live_duration:
            hours, minutes = divmod(int(duration * 60), 60)
            end = start + timedelta(hours=hours, minutes=minutes)
        return start, end

    def _parse_live_error_values(self, prefix, result):
        result_json = result.json()
        error_message = 'An error has occurred.'
        youtube_error = result_json.get('error', {})
        error_reason = youtube_error.get('errors', [{}])[0].get('reason', 'unknown')
        if error_reason == 'userRequestsExceedRateLimit':
            error_message = 'You have reached your daily broadcast limit. You may need to wait up to 24 hours before you can create another live broadcast.'
        else:
            error_message = youtube_error.get('errors', [{}])[0].get('message') or error_reason

        return {
            'state': 'failed',
            'failure_reason': f'{prefix} {error_message} ({error_reason})'
        }

    @api.model
    def _cron_post_scheduled_live_track(self):
        self.search([
            ('post_method', '=', 'scheduled'),
            ('state', '=', 'scheduled'),
            ('scheduled_date', '<=', fields.Datetime.now())
        ]).action_post_live_track()
