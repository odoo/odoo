from odoo import api, fields, models


class CalendarAlarm(models.Model):
    _inherit = "calendar.alarm"

    alarm_type = fields.Selection(
        selection_add=[("sms", "SMS Text Message")],
        ondelete={"sms": "set default"},
    )
    sms_template_id = fields.Many2one(
        comodel_name="sms.template",
        string="SMS Template",
        compute="_compute_sms_template_id",
        store=True,
        readonly=False,
        domain=[("model", "in", ["calendar.event"])],
        help="Template used to render SMS reminder content.",
    )

    @api.model
    def _get_responsible_aware_alarm_types(self):
        # An SMS reminder is sent per phone number, and `calendar_sms` skips the
        # organizer unless this flag is set -- so the flag is meaningful here.
        return super()._get_responsible_aware_alarm_types() | {"sms"}

    @api.depends("alarm_type", "sms_template_id")
    def _compute_sms_template_id(self):
        for alarm in self:
            if alarm.alarm_type == "sms" and not alarm.sms_template_id:
                alarm.sms_template_id = self.env["ir.model.data"]._xmlid_to_res_id(
                    "calendar_sms.sms_template_data_calendar_reminder"
                )
            elif alarm.alarm_type != "sms" or not alarm.sms_template_id:
                alarm.sms_template_id = False
