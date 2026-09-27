# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _get_phone_number_from_record(self, record):
        if "phone_formatted" in record and record.phone_formatted:
            return record.phone_formatted
        for field_name in record._phone_get_number_fields():
            if phone := record[field_name]:
                return phone
        return False
