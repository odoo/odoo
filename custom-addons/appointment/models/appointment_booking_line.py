# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AppointmentBookingLine(models.Model):
    _name = "appointment.booking.line"
    _rec_name = "calendar_event_id"
    _description = "Appointment Booking Line"
    _order = "event_start desc, id desc"

    active = fields.Boolean(related="calendar_event_id.active")
    appointment_resource_id = fields.Many2one('appointment.resource', string="Appointment Resource",
        ondelete="cascade", required=True)
    appointment_type_id = fields.Many2one('appointment.type', related="calendar_event_id.appointment_type_id",
        precompute=True, store=True, readonly=True, ondelete="cascade", index=True)
    capacity_reserved = fields.Integer('Capacity Reserved', default=1, required=True,
        help="Capacity reserved by the user")
    capacity_used = fields.Integer('Capacity Used', compute="_compute_capacity_used", readonly=True,
        precompute=True, store=True, help="Capacity that will be used based on the capacity and resource selected")
    calendar_event_id = fields.Many2one('calendar.event', string="Booking", ondelete="cascade", required=True)
    event_start = fields.Datetime('Booking Start', related="calendar_event_id.start", readonly=True, store=True)
    event_stop = fields.Datetime('Booking End', related="calendar_event_id.stop", readonly=True, store=True)

    _sql_constraints = [
        ('check_capacity_reserved', 'CHECK(capacity_reserved >= 0)', 'The capacity reserved should be positive.'),
        ('check_capacity_used', 'CHECK(capacity_used >= capacity_reserved)', 'The capacity used can not be lesser than the capacity reserved'),
    ]

    @api.constrains('appointment_resource_id', 'appointment_type_id')
    def _check_resources_match_appointment_type(self):
        """Check appointment resources linked to the lines are effectively usable through the appointment type."""
        for appointment_type, lines in self.grouped('appointment_type_id').items():
            non_compatible_resources = lines.appointment_resource_id - appointment_type.resource_ids
            if non_compatible_resources:
                raise ValidationError(_('"%(resource_name_list)s" cannot be used for "%(appointment_type_name)s"',
                                        appointment_type_name=appointment_type.name,
                                        resource_name_list=', '.join(non_compatible_resources.mapped('name'))))

    @api.depends('appointment_resource_id.capacity', 'appointment_resource_id.shareable',
                 'appointment_type_id.resource_manage_capacity', 'capacity_reserved')
    def _compute_capacity_used(self):
        self.capacity_used = 0
        for line in self:
            if line.capacity_reserved == 0:
                line.capacity_used = 0
            elif not line.appointment_resource_id.shareable or not line.appointment_type_id.resource_manage_capacity:
                line.capacity_used = line.appointment_resource_id.capacity
            else:
                line.capacity_used = line.capacity_reserved
