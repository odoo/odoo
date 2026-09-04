# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store


class DiscussCallHistory(models.Model):
    _name = "discuss.call.history"
    _order = "start_dt DESC, id DESC"
    _rec_name = "channel_id"
    _description = "Keep the call history"
    _explanation = "Stores the history of internal discuss calls (audio/video), tracking the start time, end time, duration, and the associated channel."

    channel_id = fields.Many2one("discuss.channel", index=True, required=True, ondelete="cascade")
    artifact_ids = fields.One2many("mail.call.artifact", "discuss_call_history_id", string="Artifacts")
    duration_hour = fields.Float(compute="_compute_duration_hour")
    has_recording = fields.Boolean(compute="_compute_has_recording")
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

    @api.depends("start_dt", "end_dt")
    def _compute_duration_hour(self):
        for record in self:
            end_dt = record.end_dt or fields.Datetime.now()
            record.duration_hour = (end_dt - record.start_dt).total_seconds() / 3600

    @api.depends("artifact_ids")
    def _compute_has_recording(self):
        for call_history in self:
            call_history.has_recording = bool(call_history.artifact_ids)

    @api.depends("artifact_ids")
    def _compute_recording_media(self):
        for call_history in self:
            mimetypes = call_history.artifact_ids.filtered(
                lambda artifact: artifact._is_recording_media()
            ).media_id.mapped("mimetype")
            call_history.has_audio = any(mimetype.startswith("audio/") for mimetype in mimetypes)
            call_history.has_video = any(mimetype.startswith("video/") for mimetype in mimetypes)

    def _broadcast_recording_availability(self):
        for call_history in self:
            call_history.invalidate_recordset([
                "artifact_ids",
                "has_audio",
                "has_recording",
                "has_video",
            ])
            Store(call_history.channel_id).add(
                call_history,
                ["has_audio", "has_recording", "has_video"],
            ).add(call_history.channel_id, ["recording_count"])
