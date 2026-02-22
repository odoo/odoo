from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_message_create_valid_field_names(self):
        return super()._get_message_create_valid_field_names() | {'tracking_value_ids'}

    def _message_create(self, values_list, tracking_values=None):
        if tracking_values:
            for values in values_list:
                values.setdefault('tracking_value_ids', [])
                for tracking_value in tracking_values:
                    if tracking_value_ids := tracking_value.pop('tracking_value_ids', []):
                        values['tracking_value_ids'].extend(tracking_value_ids)
        return super()._message_create(values_list, tracking_values)
