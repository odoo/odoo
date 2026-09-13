from odoo import api, fields, models


class MixinMailActivity(models.AbstractModel):
    _inherit = "mixin.mail.activity"

    activity_calendar_event_id = fields.Many2one(
        comodel_name="calendar.event",
        string="Next Activity Calendar Event",
        compute="_compute_activity_calendar_event_id",
        groups="base.group_user",
    )

    @api.depends(
        "activity_ids.active",
        "activity_ids.date_deadline",
        "activity_ids.calendar_event_id",
    )
    def _compute_activity_calendar_event_id(self):
        for record in self:
            record.activity_calendar_event_id = (
                record._next_activity().calendar_event_id
            )
