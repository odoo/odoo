from odoo import fields, models


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def _execute_on_registrations(self, slot_based=False):
        todo = self.filtered(
            lambda r: r.scheduler_id.notification_type == "sms"
        )
        for scheduler, reg_mails in todo.grouped('scheduler_id').items():
            if slot_based:
                scheduler._send_sms(reg_mails.mapped('slot_id.registration_ids').filtered(lambda r: r.state not in ("draft", "cancel")))
                continue
            scheduler._send_sms(reg_mails.registration_id)
        todo.mail_sent = True

        return super(EventMailRegistration, self - todo)._execute_on_registrations(slot_based)
