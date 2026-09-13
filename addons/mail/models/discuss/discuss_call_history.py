import typing

from odoo import api, fields, models

if typing.TYPE_CHECKING:
    from ..mail_message import MailMessage
    from .discuss_channel import DiscussChannel


class DiscussCallHistory(models.Model):
    _name = "discuss.call.history"
    _order = "start_dt DESC, id DESC"
    _description = "Keep the call history"

    channel_id: DiscussChannel = fields.Many2one(
        comodel_name="discuss.channel",
        index=True,
        required=True,
        ondelete="cascade",
    )
    duration_hour = fields.Float(compute="_compute_duration_hour")
    start_dt = fields.Datetime(
        index=True,
        required=True,
    )
    end_dt = fields.Datetime()
    start_call_message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        index=True,
    )

    _channel_id_not_null_constraint = models.Constraint(
        "CHECK (channel_id IS NOT NULL)", "Call history must have a channel"
    )
    _start_dt_is_not_null_constraint = models.Constraint(
        "CHECK (start_dt IS NOT NULL)", "Call history must have a start date"
    )
    _message_id_unique_constraint = models.Constraint(
        "UNIQUE (start_call_message_id)",
        "Messages can only be linked to one call history",
    )
    _channel_id_end_dt_idx = models.Index("(channel_id, end_dt) WHERE end_dt IS NULL")

    @api.depends("start_dt", "end_dt")
    def _compute_duration_hour(self) -> None:
        for record in self:
            end_dt = record.end_dt or fields.Datetime.now()
            record.duration_hour = (end_dt - record.start_dt).total_seconds() / 3600
