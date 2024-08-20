from odoo import fields, models


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def _execute_on_registrations(self):
        todo = self.filtered(
            lambda r: r.scheduler_id.notification_type == "sms"
        )
        for reg_mail in todo:
            reg_mail.registration_id._message_sms_schedule_mass(
                template=reg_mail.scheduler_id.template_ref,
                mass_keep_log=True
            )
        todo.write({'mail_sent': True})

        return super(EventMailRegistration, self - todo)._execute_on_registrations()

