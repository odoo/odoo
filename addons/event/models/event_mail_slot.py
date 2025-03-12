import logging

from odoo import api, fields, models
from odoo.addons.event.models.event_mail import _INTERVALS

_logger = logging.getLogger(__name__)


class EventMailRegistration(models.Model):
    _name = 'event.mail.slot'
    _description = 'Slot Mail Scheduler'
    _rec_name = 'scheduler_id'
    _order = 'scheduled_date DESC, id ASC'

    scheduler_id = fields.Many2one('event.mail', 'Mail Scheduler', ondelete='cascade', required=True)
    event_slot_id = fields.Many2one('event.slot', 'Slot', ondelete='cascade', required=True)
    scheduled_date = fields.Datetime('Schedule Date', compute='_compute_scheduled_date', store=True)
    error_datetime = fields.Datetime('Last Error')
    # contact and status
    last_registration_id = fields.Many2one('event.registration', 'Last Attendee')
    mail_done = fields.Boolean("Sent", copy=False, readonly=True)
    mail_state = fields.Selection(
        [('running', 'Running'), ('scheduled', 'Scheduled'), ('sent', 'Sent'), ('error', 'Error')],
        string='Global communication Status', compute='_compute_mail_state')
    mail_count_done = fields.Integer('# Sent', copy=False, readonly=True)

    @api.depends('event_slot_id.start_datetime', 'event_slot_id.end_datetime', 'scheduler_id.interval_unit', 'scheduler_id.interval_type')
    def _compute_scheduled_date(self):
        for mail_slot in self.filtered('event_slot_id'):
            scheduler = mail_slot.scheduler_id
            if scheduler.interval_type in ('before_event', 'after_event_start'):
                date, sign = mail_slot.event_slot_id.start_datetime, (scheduler.interval_type == 'before_event' and -1) or 1
            else:
                date, sign = mail_slot.event_slot_id.end_datetime, (scheduler.interval_type == 'after_event' and 1) or -1
            mail_slot.scheduled_date = date.replace(microsecond=0) + _INTERVALS[scheduler.interval_unit](sign *scheduler.interval_nbr) if date else False
