from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_message_create_valid_field_names(self):
        return super()._get_message_create_valid_field_names() | {
            'source_mailing_id',
        }

    def _get_log_valid_parameters(self):
        return super()._get_log_valid_parameters() | {
            'source_mailing_id',
        }
