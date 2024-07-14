# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_duration


class AppointmentSlot(models.Model):
    _name = "appointment.slot"
    _description = "Appointment: Time Slot"
    _rec_name = "weekday"
    _order = "weekday, start_hour, start_datetime, end_datetime"

    appointment_type_id = fields.Many2one('appointment.type', 'Appointment Type', ondelete='cascade')
    schedule_based_on = fields.Selection(related="appointment_type_id.schedule_based_on")
    slot_type = fields.Selection([('recurring', 'Recurring'), ('unique', 'One Shot')],
        string='Slot type', default='recurring', required=True, compute="_compute_slot_type", store=True,
        help="""Defines the type of slot. The recurring slot is the default type which is used for
        appointment type that are used recurringly in type like medical appointment.
        The one shot type is only used when an user create a custom appointment type for a client by
        defining non-recurring time slot (e.g. 10th of April 2021 from 10 to 11 am) from its calendar.""")
    allday = fields.Boolean('All day',
        help="Determine if the slot englobe the whole day, mainly used for unique slot type")
    restrict_to_user_ids = fields.Many2many(
        'res.users', string='Restrict to Users',
        help="If empty, all users are considered to be available.\n"
             "If set, only the selected users will be taken into account for this slot.")
    restrict_to_resource_ids = fields.Many2many("appointment.resource", string="Restrict to Resources",
        help="If empty, all resources are considered to be available.\n"
             "If set, only the selected resources will be taken into account for this slot.")
    # Recurring slot
    weekday = fields.Selection([
        ('1', 'Monday'),
        ('2', 'Tuesday'),
        ('3', 'Wednesday'),
        ('4', 'Thursday'),
        ('5', 'Friday'),
        ('6', 'Saturday'),
        ('7', 'Sunday'),
    ], string='Week Day', required=True, default='1')
    start_hour = fields.Float('Starting Hour', required=True, default=8.0)
    end_hour = fields.Float('Ending Hour', required=True, default=17.0, compute='_compute_end_hour', readonly=False,
                            store=True)
    # Real time slot
    start_datetime = fields.Datetime('From', help="Start datetime for unique slot type management")
    end_datetime = fields.Datetime('To', help="End datetime for unique slot type management")
    duration = fields.Float('Duration', compute='_compute_duration')

    _sql_constraints = [(
        'check_start_and_end_hour',
        """CHECK(
                ((end_hour=0 AND (start_hour BETWEEN 0 AND 23.99))
                    OR (start_hour BETWEEN 0 AND end_hour))
                AND (end_hour=0
                    OR (end_hour BETWEEN start_hour AND 23.99))
                )""",
        'The end time must be later than the start time.')]

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for slot in self:
            if slot.start_datetime and slot.end_datetime:
                duration = (slot.end_datetime - slot.start_datetime).total_seconds() / 3600
                slot.duration = round(duration, 2)
            else:
                slot.duration = 0

    @api.depends('appointment_type_id')
    def _compute_slot_type(self):
        for slot in self:
            slot.slot_type = 'unique' if slot.appointment_type_id.category == 'custom' else 'recurring'

    @api.depends('start_hour')
    def _compute_end_hour(self):
        """ Try to adapt end_hour if the interval end_hour < start_hour """
        for record in self:
            duration = record.appointment_type_id.appointment_duration
            if duration > 0 and record._convert_end_hour_24_format() <= record.start_hour \
                    and record.start_hour + duration <= 24:
                record.end_hour = (record.start_hour + duration) % 24

    @api.constrains('start_hour', 'end_hour')
    def _check_delta_hours(self):
        if any(self.filtered(lambda slot: slot.start_hour + slot.appointment_type_id.appointment_duration > slot._convert_end_hour_24_format() and slot.slot_type != 'unique')):
            raise ValidationError(_(
                "At least one slot duration is shorter than the meeting duration (%s hours)",
                format_duration(self.appointment_type_id.appointment_duration)
            ))

    @api.constrains('slot_type', 'start_datetime', 'end_datetime')
    def _check_unique_slot_has_datetime(self):
        if any(self.filtered(lambda slot: slot.slot_type == "unique" and not (slot.start_datetime and slot.end_datetime))):
            raise ValidationError(_("An unique type slot should have a start and end datetime"))

    def _convert_end_hour_24_format(self):
        """Convert end_hour from [0, 24[ to ]0, 24] by replacing 0 by 24 if necessary.

        The end_hour can be encoded as '00:00', which means 'the next day at midnight'.
        For some simple computation, we transform that 0 into 24 to make it easier to manipulate.
        For example, when we want to know if the end hour is after the start hour, or when looping through
        available slots 'until the end hour'.
        """
        self.ensure_one()
        return self.end_hour if self.end_hour else 24

    @api.depends('slot_type', 'weekday', 'start_datetime', 'end_datetime', 'start_hour', 'end_hour')
    def _compute_display_name(self):
        weekdays = dict(self._fields['weekday'].selection)
        for slot in self:
            if slot.slot_type == 'recurring':
                slot.display_name = "%s, %02d:%02d - %02d:%02d" % (weekdays.get(slot.weekday), int(slot.start_hour), int(round((slot.start_hour % 1) * 60)), int(slot.end_hour), int(round((slot.end_hour % 1) * 60)))
            else:
                slot.display_name = f"{slot.start_datetime} - {slot.end_datetime}"
