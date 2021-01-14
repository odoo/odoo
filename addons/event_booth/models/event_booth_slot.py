# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime


class EventBoothSlot(models.Model):
    """Even Booth Slot

    Event Booths are split into one or several Slots on which the event manager define a date range.
    Users will be able to register to one ore more slots they want to rent during the event.
    """
    _name = 'event.booth.slot'
    _description = 'Event Booth Slot'
    _order = 'booking_from asc'

    # Event / Description
    event_booth_id = fields.Many2one('event.booth', string='Booth', readonly=True, required=True)
    event_id = fields.Many2one(string='Event', related='event_booth_id.event_id', store=True)
    # The event dates are used for delimiting the min and max range for the slot booking dates in the datepicker
    event_date_begin = fields.Datetime(
        string='Event Start Date', related='event_id.date_begin')
    event_date_end = fields.Datetime(
        string='Event End Date', related='event_id.date_end')
    booking_from = fields.Datetime(
        string='Start Date', required=True)
    booking_to = fields.Datetime(
        string='End Date', required=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('unavailable', 'Unavailable'),
    ], string='Status', default='available', required=True)
    # Contact Information
    partner_id = fields.Many2one('res.partner', string='Rented By')
    topic = fields.Char(string='Topic')
    name = fields.Char(string='Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    # Registrations
    registration_ids = fields.Many2many(
        'event.booth.registration', 'event_booth_slot_booth_registration_rel',
        'booth_slot_id', 'booth_registration_id',
        string='Registrations')
    registration_count = fields.Integer(
        string='# Registrations', compute='_compute_registration_count')

    @api.constrains('booking_from', 'booking_to')
    def _check_dates(self):
        for slot in self:
            date_from = slot.booking_from
            date_to = slot.booking_to
            if date_from > date_to:
                raise ValidationError(_('Slot start date must be earlier than the end date.'))
            event_date_from = slot.event_id.date_begin
            event_date_to = slot.event_id.date_end
            event_date_from_located = format_datetime(self.env, event_date_from, tz=slot.event_id.date_tz, dt_format=False)
            event_date_to_located = format_datetime(self.env, event_date_to, tz=slot.event_id.date_tz, dt_format=False)
            if date_from < event_date_from or date_from > event_date_to:
                raise ValidationError(_(
                    'Slot start date must be included between %(start)s and %(end)s',
                    start=event_date_from_located,
                    end=event_date_to_located
                ))
            if date_to < event_date_from or date_to > event_date_to:
                raise ValidationError(_(
                    'Slot end date must be included between %(start)s and %(end)s',
                    start=event_date_from_located,
                    end=event_date_to_located
                ))
            domain = [
                ('id', '!=', slot.id),
                ('event_booth_id', '=', slot.event_booth_id.id),
                '|', '|',
                '&', ('booking_from', '<', slot.booking_from), ('booking_to', '>', slot.booking_from),
                '&', ('booking_from', '<', slot.booking_to), ('booking_to', '>', slot.booking_to),
                '&', ('booking_from', '<', slot.booking_from), ('booking_to', '>', slot.booking_to)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(_('You can not have overlapping slots.'))

    @api.depends('registration_ids')
    def _compute_registration_count(self):
        for slot in self:
            slot.registration_count = len(slot.registration_ids)

    def _get_duration_display(self, date_from=False, date_to=False):
        from_date = date_from or min(self.mapped('booking_from'))
        to_date = date_to or max(self.mapped('booking_to'))
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        return '%s \U0001F852 %s' % (
            from_date.astimezone(tz).replace(tzinfo=None),
            to_date.astimezone(tz).replace(tzinfo=None) if from_date.date() != to_date.date()
            else to_date.astimezone(tz).time()
        )

    def name_get(self):
        return [(slot.id, slot._get_duration_display(slot.booking_from, slot.booking_to)) for slot in self]

    def action_confirm(self, registration):
        if not self.is_available():
            raise ValidationError(
                _('The following slots are unavailable, please remove them from your registration : %s',
                  ''.join('\n\t- %s (%s)' % (slot.event_booth_id.name, slot.display_name) for slot in self._get_unavailable_slots())))
        self.write({
            'state': 'unavailable',
            'partner_id': registration.partner_id,
            'name': registration.contact_name,
            'email': registration.contact_email,
            'phone': registration.contact_phone,
            'mobile': registration.contact_mobile,
        })
        self._message_post_booth_id(_('Registration confirmed by <b>%s</b> for the following slots: <ul>%s</ul>'))

    def action_cancel(self):
        old_partner_id = self.partner_id
        self.write({
            'state': 'available',
            'partner_id': False,
            'name': False,
            'email': False,
            'phone': False,
            'mobile': False,
        })
        self._message_post_booth_id(
            _('<b>%s</b>\'s registration has been cancelled, the following slots becomes <b>available</b>: <ul>%s</ul>'),
            old_partner_id.name)

    def action_reserve(self):
        self.write({
            'state': 'reserved',
            'partner_id': self.env.user.partner_id.id,
        })
        self._message_post_booth_id(_('The following slots have been reserved by <b>%s</b>: <ul>%s</ul>'))

    def action_create_new_registration(self):
        return {
            'name': _('Registration'),
            'type': 'ir.actions.act_window',
            'res_model': 'event.booth.registration',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'search_default_event_booth_id': self.event_booth_id.id,
                'default_booth_slot_ids': self.ids
            },
        }

    def _message_post_booth_id(self, message_body, partner_name=False):
        self.event_booth_id.message_post(
            author_id=self.env.ref('base.partner_root').id,
            subject='Event Booth Registration Changed',
            body=message_body % (partner_name or self.partner_id.name, ''.join('<li>%s</li>' % slot.display_name for slot in self)),
            message_type='comment'
        )

    def is_available(self):
        return not any(slot.state in ['unavailable', 'reserved'] for slot in self)

    def _get_unavailable_slots(self):
        return self.filtered(lambda slot: slot.state in ['unavailable', 'reserved'])
