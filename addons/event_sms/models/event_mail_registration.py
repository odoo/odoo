from odoo import fields, models
from odoo.addons import event


class EventMailRegistration(event.EventMailRegistration):

    def _execute_on_registrations(self):
        todo = self.filtered(
            lambda r: r.scheduler_id.notification_type == "sms"
        )
        for scheduler, reg_mails in todo.grouped('scheduler_id').items():
            scheduler._send_sms(reg_mails.registration_id)
        todo.mail_sent = True

        return super(EventMailRegistration, self - todo)._execute_on_registrations()
