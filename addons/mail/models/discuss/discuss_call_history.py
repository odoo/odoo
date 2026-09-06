# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

from odoo.addons.mail.tools.call import format_call_duration


class DiscussCallHistory(models.Model):
    _name = "discuss.call.history"
    _order = "start_dt DESC, id DESC"
    _description = "Keep the call history"
    _explanation = "Stores the history of internal discuss calls (audio/video), tracking the start time, end time, duration, and the associated channel."

    channel_id = fields.Many2one("discuss.channel", index=True, required=True, ondelete="cascade")
    artifact_ids = fields.One2many("mail.call.artifact", "discuss_call_history_id", string="Artifacts")
    duration_hour = fields.Float(compute="_compute_duration_hour")
    activity_done_label = fields.Char(
        compute="_compute_activity_done_label", export_string_translation=False)
    duration_human_readable = fields.Char(
        compute="_compute_duration_human_readable", export_string_translation=False)
    has_recording = fields.Boolean(compute="_compute_has_recording")
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

    @api.depends("start_dt", "end_dt")
    def _compute_duration_hour(self):
        for record in self:
            end_dt = record.end_dt or fields.Datetime.now()
            record.duration_hour = (end_dt - record.start_dt).total_seconds() / 3600

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

    @api.depends("artifact_ids")
    def _compute_has_recording(self):
        for record in self:
            record.has_recording = bool(record.artifact_ids)

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
            },
        }

    def _link_to_activity(self):
        """ Link the call to the activity that planned it, if any, so that the
        call shows up in the chatter of the document holding that activity. """
        for record in self.filtered(lambda record: not record.activity_id):
            record.activity_id = record._get_activity_to_link()

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
