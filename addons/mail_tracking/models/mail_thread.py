from odoo.exceptions import UserError
from odoo import fields, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_message_create_valid_field_names(self):
        return super()._get_message_create_valid_field_names() | {'tracking_value_ids'}

    def _check_can_update_message_content(self, messages):
        """" Checks that the current user can update the content of the message.
          * if no tracking;
        """
        super()._check_can_update_message_content(messages)
        if messages.tracking_value_ids:
            raise UserError(self.env._("Messages with tracking values cannot be modified"))

    def _message_create(self, values_list, tracking_values=None):
        if tracking_values:
            for values in values_list:
                values.setdefault('tracking_value_ids', [])
                for tracking_value in tracking_values:
                    values['tracking_value_ids'].extend([fields.Command.create(tracking_value)])
        return super()._message_create(values_list, tracking_values)
