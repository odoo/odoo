# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    phone_formatted = fields.Char(compute="_compute_phone_formatted")

    @api.depends("phone", "res_model", "res_ids")
    def _compute_phone_formatted(self):
        for activity in self:
            records = activity._get_applied_on_records()
            activity.phone_formatted = (
                records._phone_get_formatted(activity.phone)
                if activity.phone and len(records) == 1
                else activity.phone
            )

    def _get_phone_number(self, record):
        record = record.exists()
        if not record:
            return False
        record.check_access("read")
        recipient_info = record._phone_get_recipients_info()[record.id]
        return recipient_info["number"]
