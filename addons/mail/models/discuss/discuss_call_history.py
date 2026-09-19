# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import format_datetime

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.duration import format_seconds


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
    activity_done_message_id = fields.Many2one("mail.message", index="btree_not_null")
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
        self._rerender_activity_done_message()
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

    @api.depends("start_dt", "end_dt")
    def _compute_duration_human_readable(self):
        for record in self:
            end_dt = record.end_dt or fields.Datetime.now()
            record.duration_human_readable = format_seconds(
                self.env, round((end_dt - record.start_dt).total_seconds()),
            )

    def action_log_meeting(self):
        """ Open the wizard logging this call as an activity on a document. """
        self.ensure_one()
        return {
            "name": self.env._("Log Activity in Chatter"),
            "type": "ir.actions.act_window",
            "res_model": "mail.activity.schedule.call",
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
        """ The other partners in the call. The document it gets logged on is most
        likely about one of them, so the wizard ranks their records first. """
        self.ensure_one()
        # sudo: discuss.channel: who a call was held with does not depend on the reader
        # being a member of its channel.
        partners = self.channel_id.sudo().channel_partner_ids
        return partners - self.env.user.partner_id

    def _is_call_ongoing(self):
        """ Whether the call is still being held. """
        self.ensure_one()
        return not self.end_dt

    def _link_to_logged_activity(self, activity, partner):
        """ Remember the activity the call was logged as, so that the call shows up in
        the chatter of the document that activity is on. A call already reporting on an
        activity keeps it: it was logged while it was still going on. """
        self.ensure_one()
        self.check_access('read')
        # sudo: discuss.call.history: no one may write a call history, yet whoever attended
        # the call may log it on a document of theirs.
        call_history = self.sudo()
        if not call_history.activity_id:
            call_history.activity_id = activity

    def _link_and_complete_activity(self):
        """ Link the call to the activity that planned it, if any, so that the
        call shows up in the chatter of the document holding that activity, and
        mark that activity as done since the meeting it planned took place. """
        for record in self:
            # a call logged while it was still going on already has its activity, left
            # pending until the call it reports on actually ends: complete that one
            # rather than looking for another.
            activity = record.activity_id
            if not activity:
                activity = record._get_activity_to_link()
                record.activity_id = activity
            if not activity or activity.date_done:
                continue
            message_id = activity.with_user(activity.user_id).sudo().action_done()
            if message_id:
                # the activity is done only once the call ends, but the message
                # should still read as having taken place when the call did.
                self.env["mail.message"].browse(message_id).date = record.start_dt

    def _rerender_activity_done_message(self):
        """ Re-render the chatter message logging this call: the artifacts it announces
        only land once the call is over, hence after it was first rendered. Runs in the
        elevated context its callers already establish. """
        view = self.env.ref("mail.message_activity_done")
        stores = Store.Stores()
        for record in self.filtered("activity_done_message_id"):
            message = record.activity_done_message_id
            activity = record.activity_id
            if not activity or not message.model or not message.res_id:
                continue
            bodies = self.env["mail.render.mixin"]._render_template_qweb_view(
                view, message.model, [message.res_id],
                add_context={
                    "activity": activity,
                    "display_assignee": activity.user_id.partner_id != message.author_id,
                    "feedback": activity.feedback,
                    **self.env["mail.activity"]._get_activity_done_message_extra_values(activity),
                },
            )
            if body := bodies.get(message.res_id):
                message.body = body
                stores[message].add(message, ["body"])

    def _get_activity_to_link(self):
        """ The activity that planned this call, void when it was not planned: a module
        able to tie a call back to an activity overrides this. """
        self.ensure_one()
        return self.env["mail.activity"]

    def _get_log_contact(self):
        """ The contact the call is logged on by default, void when unknown: a module
        knowing who the call was with overrides this. """
        self.ensure_one()
        return self.env["res.partner"]
