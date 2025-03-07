import logging

from odoo import api, fields, models
from odoo.addons.event.models.event_mail import _INTERVALS
from odoo.exceptions import MissingError


_logger = logging.getLogger(__name__)


class EventMailRegistration(models.Model):
    _name = 'event.mail.registration'
    _description = 'Registration Mail Scheduler'
    _rec_name = 'scheduler_id'
    _order = 'scheduled_date DESC, id ASC'

    scheduler_id = fields.Many2one('event.mail', 'Mail Scheduler', required=True, ondelete='cascade')
    registration_id = fields.Many2one('event.registration', 'Attendee', ondelete='cascade')
    slot_id = fields.Many2one('event.slot', 'Slot', ondelete='cascade')
    scheduled_date = fields.Datetime('Scheduled Time', compute='_compute_scheduled_date', store=True)
    mail_sent = fields.Boolean('Mail Sent')

    @api.depends('registration_id', 'slot_id', 'scheduler_id.interval_unit', 'scheduler_id.interval_type')
    def _compute_scheduled_date(self):
        for mail in self:
            if mail.registration_id:
                mail.scheduled_date = mail.registration_id.create_date.replace(microsecond=0) + _INTERVALS[mail.scheduler_id.interval_unit](mail.scheduler_id.interval_nbr)
            elif mail.slot_id:
                if mail.scheduler_id.interval_type in ('before_event', 'after_event_start'):
                    date, sign = mail.slot_id.start_datetime, (mail.scheduler_id.interval_type == 'before_event' and -1) or 1
                else:
                    date, sign = mail.slot_id.end_datetime, (mail.scheduler_id.interval_type == 'after_event' and 1) or -1
                mail.scheduled_date = date.replace(microsecond=0) + _INTERVALS[mail.scheduler_id.interval_unit](sign * mail.scheduler_id.interval_nbr) if date else False
            else:
                mail.scheduled_date = False

    def execute(self, slot_based=False):
        # Deprecated, to be called only from parent scheduler
        skip_domain = self._get_skip_domain()
        if not slot_based:
            skip_domain += [("registration_id.state", "in", ("open", "done"))]
        self.filtered_domain(skip_domain)._execute_on_registrations()

    def _execute_on_registrations(self, slot_based=False):
        """ Private mail registration execution. We consider input is already
        filtered at this point, allowing to let caller do optimizations when
        managing batches of registrations. """
        todo = self.filtered(
            lambda r: r.scheduler_id.notification_type == "mail"
        )
        for scheduler, reg_mails in todo.grouped('scheduler_id').items():
            if slot_based:
                scheduler._send_mail(reg_mails.mapped('slot_id.registration_ids').filtered(lambda r: r.state not in ("draft", "cancel")))
                continue
            scheduler._send_mail(reg_mails.registration_id)
        todo.mail_sent = True
        return todo

    def _get_skip_domain(self):
        """ Domain of mail registrations ot skip: not already done, linked to
        a valid registration, and scheduled in the past. """
        return [
            ("mail_sent", "=", False),
            ("scheduled_date", "!=", False),
            ("scheduled_date", "<=", self.env.cr.now()),
        ]
