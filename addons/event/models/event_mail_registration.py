import logging

from odoo import api, fields, models
from odoo.addons.event.models.event_mail import _INTERVALS
from odoo.exceptions import MissingError


_logger = logging.getLogger(__name__)


class EventMailRegistration(models.Model):
    _name = 'event.mail.registration'
    _description = 'Registration Mail Scheduler'
    _rec_name = 'scheduler_id'
    _order = 'scheduled_date DESC'

    scheduler_id = fields.Many2one('event.mail', 'Mail Scheduler', required=True, ondelete='cascade')
    registration_id = fields.Many2one('event.registration', 'Attendee', required=True, ondelete='cascade')
    scheduled_date = fields.Datetime('Scheduled Time', compute='_compute_scheduled_date', store=True)
    mail_sent = fields.Boolean('Mail Sent')

    @api.depends('registration_id', 'scheduler_id.interval_unit', 'scheduler_id.interval_type')
    def _compute_scheduled_date(self):
        for mail in self:
            if mail.registration_id:
                mail.scheduled_date = mail.registration_id.create_date.replace(microsecond=0) + _INTERVALS[mail.scheduler_id.interval_unit](mail.scheduler_id.interval_nbr)
            else:
                mail.scheduled_date = False

    def execute(self):
        self.filtered_domain(self._get_skip_domain())._execute_on_registrations()

    def _execute_on_registrations(self):
        """ Private mail registration execution. We consider input is already
        filtered at this point, allowing to let caller do optimizations when
        managing batches of registrations. """
        todo = self.filtered(
            lambda r: r.scheduler_id.notification_type == "mail"
        )
        done = self.browse()
        for reg_mail in todo:
            organizer = reg_mail.scheduler_id.event_id.organizer_id
            company = self.env.company
            author = self.env.ref('base.user_root').partner_id
            if organizer.email:
                author = organizer
            elif company.email:
                author = company.partner_id
            elif self.env.user.email:
                author = self.env.user.partner_id

            template = reg_mail.scheduler_id.template_ref
            email_values = {
                'author_id': author.id,
            }
            if not template.email_from:
                email_values['email_from'] = author.email_formatted
            template.send_mail(reg_mail.registration_id.id, email_values=email_values)
            done += reg_mail
        done.write({'mail_sent': True})
        return done

    def _get_skip_domain(self):
        """ Domain of mail registrations ot skip: not already done, linked to
        a valid registration, and scheduled in the past. """
        return [
            ("mail_sent", "=", False),
            ("registration_id.state", "in", ("open", "done")),
            ("scheduled_date", "!=", False),
            ("scheduled_date", "<=", fields.Datetime.now()),
        ]
