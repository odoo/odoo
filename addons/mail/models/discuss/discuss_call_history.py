# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import format_datetime

from odoo.addons.mail.tools.discuss import Store

from odoo.addons.mail.tools.call import format_call_duration


class DiscussCallHistory(models.Model):
    _name = "discuss.call.history"
    _order = "start_dt DESC, id DESC"
    _rec_names_search = ("channel_id",)
    _description = "Keep the call history"
    _explanation = "Stores the history of internal discuss calls (audio/video), tracking the start time, end time, duration, and the associated channel."

    channel_id = fields.Many2one("discuss.channel", index=True, required=True, ondelete="cascade")
    artifact_ids = fields.One2many("mail.call.artifact", "discuss_call_history_id", string="Artifacts")
    duration_hour = fields.Float(compute="_compute_duration_hour")
    activity_done_label = fields.Char(
        compute="_compute_activity_done_label", export_string_translation=False)
    duration_human_readable = fields.Char(
        compute="_compute_duration_human_readable", export_string_translation=False)
    has_recording = fields.Boolean(compute="_compute_recording_media")
    has_audio = fields.Boolean(compute="_compute_recording_media")
    has_video = fields.Boolean(compute="_compute_recording_media")
    start_dt = fields.Datetime(index=True, required=True)
    end_dt = fields.Datetime()
    start_call_message_id = fields.Many2one("mail.message", index=True)
    activity_id = fields.Many2one("mail.activity", index="btree_not_null")
    activity_res_model = fields.Char(related="activity_id.res_model")
    activity_res_id = fields.Many2oneReference(
        related="activity_id.res_id",
        string="Logged On (ID)",
        model_field="activity_res_model",
    )

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

    @api.depends("duration_human_readable")
    def _compute_activity_done_label(self):
        for record in self:
            record.activity_done_label = self.env._(
                "Meeting done (%(duration)s)", duration=record.duration_human_readable,
            )

    @api.depends("duration_hour")
    def _compute_duration_human_readable(self):
        for record in self:
            record.duration_human_readable = format_call_duration(self.env, round(record.duration_hour * 3600))

    def action_log_meeting(self):
        """ Open the Log Activity wizard for this call, so that it gets linked to
        an activity on the document of the user's choice.

        :return: an action dictionary opening the ``mail.activity.schedule`` wizard"""
        self.ensure_one()
        return {
            "name": self.env._("Log Activity in Chatter"),
            "type": "ir.actions.act_window",
            "res_model": "mail.activity.schedule",
            "view_mode": "form",
            "views": [(self.env.ref("mail.mail_activity_log_view_form").id, "form")],
            "target": "new",
            "context": {
                "default_activity_type_id": self.env.ref("mail.mail_activity_data_meeting").id,
                "default_call_history_id": self.id,
                "default_date_deadline": False,
                "default_res_model_selection": "res.partner",
                "log_contact_id": self._get_log_contact().id,
                "log_channel_partner_ids": self._get_log_channel_partners().ids,
                "log_activity_category": "meeting",
            },
        }

    def _get_log_channel_partners(self):
        """ Return the partners the call was held with, the user logging it aside: who the
        document it gets logged on is expected to be about
        (see `mail.activity.mixin.name_search`).

        :return: a ``res.partner`` recordset"""
        self.ensure_one()
        # sudo: discuss.channel: who a call was held with does not depend on the reader
        # being a member of its channel.
        partners = self.channel_id.sudo().channel_partner_ids
        return partners - self.env.user.partner_id

    def _link_to_activity(self):
        """ Link the call to the activity that planned it, if any, so that the
        call shows up in the chatter of the document holding that activity, and
        mark that activity as done since the meeting it planned took place. """
        for record in self.filtered(lambda record: not record.activity_id):
            activity = record._get_activity_to_link()
            record.activity_id = activity
            if activity:
                message_id = activity.action_done()
                if message_id:
                    # the activity is done only once the call ends, but the message
                    # should still read as having taken place when the call did.
                    self.env["mail.message"].browse(message_id).date = record.start_dt

    def _get_activity_to_link(self):
        """ Return the activity that planned this call. Modules able to tie a
        call back to an activity (e.g. calendar, through the meeting the call
        happens in) override this method.

        :return: a ``mail.activity`` recordset, void when the call was not planned"""
        self.ensure_one()
        return self.env["mail.activity"]

    def _get_log_contact(self):
        """ Return the contact the call should be logged on by default. Modules
        knowing who the call was with (e.g. calendar, for the meeting organizer)
        override this method.

        :return: a ``res.partner`` recordset, void when it cannot be determined"""
        self.ensure_one()
        return self.env["res.partner"]
