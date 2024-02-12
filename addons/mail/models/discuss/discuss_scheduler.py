# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class DiscussScheduler(models.Model):
    _name = "discuss.scheduler"
    _description = "Schedule a date to send a message"

    message_data = fields.Json()
    date = fields.Datetime()
    thread_model = fields.Char()
    thread_id = fields.Integer()

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
