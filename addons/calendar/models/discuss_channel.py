from odoo import fields, models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    calendar_event_ids = fields.One2many(
        comodel_name="calendar.event",
        inverse_name="videocall_channel_id",
    )

    def _is_call_invitation_required(self):
        if self.calendar_event_ids:
            return False
        return super()._is_call_invitation_required()
