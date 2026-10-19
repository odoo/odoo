# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import format_datetime

from odoo.addons.mail.tools.discuss import Store


class DiscussCallHistory(models.Model):
    _name = "discuss.call.history"
    _order = "start_dt DESC, id DESC"
    _rec_names_search = ("channel_id",)
    _description = "Keep the call history"
    _explanation = "Stores the history of internal discuss calls (audio/video), tracking the start time, end time, duration, and the associated channel."

    channel_id = fields.Many2one("discuss.channel", index=True, required=True, ondelete="cascade")
    artifact_ids = fields.One2many("mail.call.artifact", "discuss_call_history_id", string="Artifacts")
    duration_hour = fields.Float(compute="_compute_duration_hour")
    has_recording = fields.Boolean(compute="_compute_recording_media")
    has_audio = fields.Boolean(compute="_compute_recording_media")
    has_video = fields.Boolean(compute="_compute_recording_media")
    start_dt = fields.Datetime(index=True, required=True)
    end_dt = fields.Datetime()
    start_call_message_id = fields.Many2one("mail.message", index=True)

    _channel_id_not_null_constraint = models.Constraint(
        "CHECK (channel_id IS NOT NULL)", "Call history must have a channel"
    )
    _start_dt_is_not_null_constraint = models.Constraint(
        "CHECK (start_dt IS NOT NULL)", "Call history must have a start date"
    )
    _message_id_unique_constraint = models.Constraint(
        "UNIQUE (start_call_message_id)", "Messages can only be linked to one call history"
    )
    _channel_id_end_dt_idx = models.Index("(channel_id, end_dt) WHERE end_dt IS NULL")

    @api.ondelete(at_uninstall=False)
    def _unlink_cleanup_artifacts_attachments(self):
        self.artifact_ids.unlink()

    @api.depends("channel_id.display_name", "start_dt")
    @api.depends_context("lang", "tz", "uid")
    def _compute_display_name(self):
        for call_history in self:
            started_at = format_datetime(
                self.env,
                call_history.start_dt,
                tz=self.env.context.get("tz"),
            )
            call_history.display_name = (
                f"{call_history.channel_id.display_name} - {started_at}"
            )

    @api.depends("start_dt", "end_dt")
    def _compute_duration_hour(self):
        for record in self:
            end_dt = record.end_dt or fields.Datetime.now()
            record.duration_hour = (end_dt - record.start_dt).total_seconds() / 3600

    # media_id.mimetype also affects these fields, but media_id is not searchable.
    # Recording flows preserve MIME after creation. If that changes, update the
    # dependency tracking or explicitly invalidate these fields.
    @api.depends("artifact_ids.media_id", "artifact_ids.recording_upload_pending")
    def _compute_recording_media(self):
        for call_history in self:
            mimetypes = call_history.artifact_ids.filtered(
                lambda artifact: artifact._is_recording_media(),
            ).media_id.mapped("mimetype")
            call_history.has_audio = any(
                mimetype.startswith("audio/") for mimetype in mimetypes
            )
            call_history.has_video = any(
                mimetype.startswith("video/") for mimetype in mimetypes
            )
            call_history.has_recording = call_history.has_audio or call_history.has_video

    def _broadcast_recording_availability(self):
        for call_history in self:
            Store(call_history.channel_id).add(
                call_history,
                lambda res: (
                    res.one("channel_id", []),
                    res.attr("has_audio"),
                    res.attr("has_recording"),
                    res.attr("has_video"),
                ),
            )
