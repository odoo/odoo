from collections import defaultdict

from odoo import models


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def _execute_on_registrations(self):
        todo = self.filtered(
            lambda r: r.scheduler_id.notification_type == "whatsapp"
        )
        # Create whatsapp composer and send message by cron
        for scheduler, reg_mails in todo.grouped('scheduler_id').items():
            scheduler._send_whatsapp(reg_mails.registration_id)
        todo.mail_sent = True

        return super(EventMailRegistration, self - todo)._execute_on_registrations()
