# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class DiscussScheduler(models.Model):
    _name = "discuss.scheduler"
    _description = "Schedule a date to send a message"

    message_data = fields.Json()
    date = fields.Datetime()
    thread_model = fields.Char()
    thread_id = fields.Integer()
    author_id = fields.Many2one('res.partner')

    def _send_scheduled_message_cron(self):
        messages = self.env["discuss.scheduler"].search([])
        for message in messages:
            thread = self.env[message.thread_model].search([("id", "=", message.thread_id)])
            thread.with_user(message.create_uid).message_post(**message.message_data)
            message.unlink()

    def get_messages(self):
        messages = self.read()
        data = []
        for message in messages:
            data.append(message["message_data"])
        return data

    def _message_scheduled_format(self):
        data = []
        for message in self:
            data.append({
                "id": message.id,
                "thread": {
                    "model": message.thread_model,
                    "id": message.thread_id
                },
                "message": {
                    "id": f"scheduled_{message.id}",
                    "author": message.author_id.mail_partner_format().get(message.author_id),
                    "body": message.message_data["body"],
                    'is_note': message.message_data["subtype_xmlid"] == "mail.mt_note",
                    'is_discussion': message.message_data["subtype_xmlid"] == "mail.mt_comment",
                    "thread": {
                        "model": message.thread_model,
                        "id": message.thread_id
                    },
                    "date": fields.Datetime.to_string(message.date),
                    "is_scheduled": True,
                },
            })
        return data
