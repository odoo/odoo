from odoo import fields, models


class MailScheduledMessage(models.Model):
    _inherit = "mail.scheduled.message"

    account_reports_annotation_date = fields.Date(string="Annotated For")

    def _message_created_hook(self, message):
        """Hook called when a message is created from the scheduled message.

        :param record message: the created mail.message record
        """
        super()._message_created_hook(message)
        if self.account_reports_annotation_date:
            self.env["account.report.annotation"].with_user(self.create_uid).create(
                {
                    "date": self.account_reports_annotation_date,
                    "message_id": message.id,
                }
            )
