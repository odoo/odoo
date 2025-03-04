from datetime import timedelta

from odoo import fields, models, _
from odoo.tools import html2plaintext


class EventTrackPostWizard(models.TransientModel):
    _name = 'event.track.post.wizard'
    _description = 'Event Track Post Wizard'

    youtube_account_id = fields.Many2one('event.track.live.account', required=True)
    youtube_privacy = fields.Selection([
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
        ('private', 'Private')], default='unlisted', required=True)

    post_method = fields.Selection([
        ('now', 'Send now'),
        ('scheduled', 'Schedule later')], string="When", default='now', required=True,
        help="Publish your post immediately or schedule it at a later time.")
    publish_hour_offset_before = fields.Integer(string="Publish Offset (Hours)", default=2,
        help="Number of hours before the scheduled start time to publish the post.")
    post_ids = fields.Many2many('event.track.live.post')

    is_valid = fields.Boolean(default=True)
    is_partial = fields.Boolean()
    warning_message = fields.Char()


    def action_post(self):
        self.ensure_one()

        model = 'event.track'
        active_ids = self.env.context.get('active_ids', [])
        active_tracks = self.env[model].browse(active_ids)

        tracks = active_tracks.filtered(lambda track: track.date and (not track.youtube_post_id or track.youtube_post_id.state == 'draft'))
        self.is_partial = False
        if not tracks:
            self.is_valid = False
            self.warning_message = _('Some records are already posted or without date, no records are available for posting!')
            return

        ignored_count = len(active_tracks) - len(tracks)
        if ignored_count and not self.is_partial:
            self.warning_message = _("Some records are already posted or without date, %(ignored_count)s records have been ignored!", ignored_count=ignored_count)

        for track in tracks:
            self._create_track_live_post(track)

        if len(tracks) > 10:
            self.is_partial = True
            tracks = tracks[:10]
            self.warning_message = _('You have more than 10 records to post, manual batching started!')

        if self.post_method == 'scheduled':
            tracks.youtube_post_id.action_schedule_live_track()
        else:
            tracks.youtube_post_id.action_post_live_track()

        for post in tracks.youtube_post_id.filtered(lambda p: p.state == 'failed'):
            post.youtube_video_id = False

        self.post_ids += tracks.youtube_post_id

        if len(active_ids) == 1 and self.post_ids:
            return self._open_social_post()

        return self._return_wizard_action(active_ids)

    def _open_social_post(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'event.track.live.post',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.post_ids.id,
        }

    def _return_wizard_action(self, active_ids):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'event.track.post.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'context': {'active_ids': active_ids},
            'target': 'new',
        }

    def action_see_posts(self):
        action = self.env.ref('website_event_track_live.action_event_track_live_post').read()[0]
        action.update({
            'domain': [(('id', 'in', self.post_ids.ids))],
        })
        return action

    def _prepare_youtube_post_values(self, track):
        self.ensure_one()

        title = track.name or str(track)
        title = f'{title[:95]}\n...' if len(title) > 100 else title
        description = html2plaintext(track.description or '')
        description = f'{description[:4995]}\n...' if len(description) > 5000 else description
        post_values = {
            'account_id': self.youtube_account_id.id,
            'post_method': self.post_method,
            'youtube_live_start_time': track.date,
            'youtube_live_duration': track.duration,
            'name': title,
            'description': description,
            'youtube_video_privacy': self.youtube_privacy,
            'event_track_id': track.id,
        }
        if self.post_method == 'scheduled':
            post_values['scheduled_date'] = track.date - timedelta(hours=abs(self.publish_hour_offset_before))
        return post_values

    def _create_track_live_post(self, track):
        if track.youtube_post_id:
            return
        post_values = self._prepare_youtube_post_values(track)
        post = self.env['event.track.live.post'].create(post_values)
        track.youtube_post_id = post.id
