# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
import logging
from datetime import datetime, timedelta

from odoo import _, api, Command, fields, models, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext, email_normalize, email_split_tuples
from odoo.addons.appointment.utils import invert_intervals
from odoo.addons.resource.models.utils import Intervals, timezone_datetime
from ..utils import interval_from_events, intervals_overlap

_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # If the event has an apt type, set the event stop datetime to match the apt type duration
        if res.get('appointment_type_id') and res.get('duration') and res.get('start') and 'stop' in fields_list:
            res['stop'] = res['start'] + timedelta(hours=res['duration'])
        if not self.env.context.get('booking_gantt_create_record', False):
            return res
        # Round the stop datetime to the nearest minute when coming from the gantt view
        if res.get('stop') and isinstance(res['stop'], datetime) and res['stop'].second != 0:
            res['stop'] = datetime.min + round((res['stop'] - datetime.min) / timedelta(minutes=1)) * timedelta(minutes=1)
        user_id = res.get('user_id')
        resource_ids = self.env.context.get('default_resource_ids', [])
        # get a relevant appointment type for ease of use when coming from a view that groups by resource
        if not res.get('appointment_type_id') and 'appointment_type_id' in fields_list:
            appointment_types = False
            if resource_ids:
                appointment_types = self.env['appointment.resource'].browse(resource_ids).appointment_type_ids
            elif user_id:
                appointment_types = self.env['appointment.type'].search([('staff_user_ids', 'in', user_id)])
            if appointment_types:
                res['appointment_type_id'] = appointment_types[0].id
        if self.env.context.get('appointment_default_assign_user_attendees'):
            default_partner_ids = self.env.context.get('default_partner_ids', [])
            # If there is only one attendee -> set him as organizer of the calendar event
            # Mostly used when you click on a specific slot in the appointment kanban
            if len(default_partner_ids) == 1 and 'user_id' in fields_list:
                attendee_user = self.env['res.partner'].browse(default_partner_ids).user_ids
                if attendee_user:
                    res['user_id'] = attendee_user[0].id
            # Special gantt case: we want to assign the current user to the attendees if he's set as organizer
            elif res.get('user_id') and res.get('partner_ids', Command.set([])) == [Command.set([])] and \
                res['user_id'] == self.env.uid and 'partner_ids' in fields_list:
                res['partner_ids'] = [Command.set(self.env.user.partner_id.ids)]
        return res

    def _default_access_token(self):
        return str(uuid.uuid4())

    access_token = fields.Char('Access Token', default=_default_access_token, readonly=True)
    alarm_ids = fields.Many2many(compute='_compute_alarm_ids', store=True, readonly=False)
    appointment_answer_input_ids = fields.One2many('appointment.answer.input', 'calendar_event_id', string="Appointment Answers")
    appointment_attended = fields.Boolean('Attendees Arrived')
    appointment_type_id = fields.Many2one('appointment.type', 'Appointment', tracking=True)
    appointment_type_schedule_based_on = fields.Selection(related="appointment_type_id.schedule_based_on")
    appointment_type_manage_capacity = fields.Boolean(related="appointment_type_id.resource_manage_capacity")
    appointment_invite_id = fields.Many2one('appointment.invite', 'Appointment Invitation', readonly=True, ondelete='set null')
    # currently unused but kept because of stable constraint, properly removed by: https://github.com/odoo/enterprise/commit/dea2f65fcb106848c9f1985e3d49f177c597fe71
    appointment_resource_id = fields.Many2one('appointment.resource', string="Appointment Resource",
                                              compute="_compute_appointment_resource_id", inverse="_inverse_appointment_resource_id_or_capacity",
                                              store=True, group_expand="_read_group_appointment_resource_id")
    appointment_resource_ids = fields.Many2many('appointment.resource', 'appointment_booking_line', 'calendar_event_id', 'appointment_resource_id',
                                                string="Appointment Resources", group_expand="_read_group_appointment_resource_id",
                                                depends=['booking_line_ids'], readonly=True)
    # This field is used in the form view to create/manage the booking lines based on the resource_total_capacity_reserved
    # selected. This allows to have the appointment_resource_ids field linked to the appointment_booking_line model and
    # thus avoid the duplication of information.
    resource_ids = fields.Many2many('appointment.resource', string="Resources",
                                    compute="_compute_resource_ids", inverse="_inverse_resource_ids_or_capacity",
                                    group_expand="_read_group_appointment_resource_id")
    booking_line_ids = fields.One2many('appointment.booking.line', 'calendar_event_id', string="Booking Lines")
    partner_ids = fields.Many2many('res.partner', group_expand="_read_group_partner_ids")
    resource_total_capacity_reserved = fields.Integer('Total Capacity Reserved', compute="_compute_resource_total_capacity", inverse="_inverse_appointment_resource_id_or_capacity")
    resource_total_capacity_used = fields.Integer('Total Capacity Used', compute="_compute_resource_total_capacity")
    user_id = fields.Many2one('res.users', group_expand="_read_group_user_id")
    videocall_redirection = fields.Char('Meeting redirection URL', compute='_compute_videocall_redirection')
    appointment_booker_id = fields.Many2one('res.partner', string="Person who is booking the appointment", index='btree_not_null')
    resources_on_leave = fields.Many2many('appointment.resource', string='Resources intersecting with leave time', compute="_compute_resources_on_leave")
    _sql_constraints = [
        ('check_resource_and_appointment_type',
         "CHECK(appointment_resource_id IS NULL OR (appointment_resource_id IS NOT NULL AND appointment_type_id IS NOT NULL))",
         "An event cannot book resources without an appointment type.")
    ]

    @api.constrains('appointment_resource_ids', 'appointment_type_id')
    def _check_resource_and_appointment_type(self):
        for event in self:
            if event.appointment_resource_ids and not event.appointment_type_id:
                raise ValidationError(_("The event %s cannot book resources without an appointment type.", event.name))

    @api.depends('appointment_type_id')
    def _compute_alarm_ids(self):
        for event in self.filtered('appointment_type_id'):
            if not event.alarm_ids:
                event.alarm_ids = event.appointment_type_id.reminder_ids

    @api.depends('booking_line_ids.appointment_resource_id')
    def _compute_appointment_resource_id(self):
        for event in self:
            if len(event.booking_line_ids) == 1:
                event.appointment_resource_id = event.booking_line_ids.appointment_resource_id
            else:
                event.appointment_resource_id = False

    @api.depends('booking_line_ids', 'booking_line_ids.appointment_resource_id')
    def _compute_resource_ids(self):
        for event in self:
            event.resource_ids = event.booking_line_ids.appointment_resource_id

    @api.depends('start', 'stop', 'appointment_resource_ids', 'appointment_resource_id')
    def _compute_resources_on_leave(self):
        resource_events = self.filtered(lambda event: event.appointment_resource_ids or event.appointment_resource_id)
        (self - resource_events).resources_on_leave = False
        if not resource_events:
            return

        for start, stop, events in interval_from_events(resource_events):
            group_resources = events.appointment_resource_ids | events.appointment_resource_id
            unavailabilities = group_resources.sudo().resource_id._get_unavailable_intervals(start, stop)
            for event in events:
                event_resources = event.appointment_resource_ids | event.appointment_resource_id
                event.resources_on_leave = event_resources.filtered(lambda resource: any(
                    intervals_overlap(interval, (event.start, event.stop)) for interval
                    in unavailabilities.get(resource.resource_id.id, [])
                ))

    @api.depends('booking_line_ids')
    def _compute_resource_total_capacity(self):
        booking_data = self.env['appointment.booking.line']._read_group(
            [('calendar_event_id', 'in', self.ids)],
            ['calendar_event_id'],
            ['capacity_reserved:sum', 'capacity_used:sum'],
        )
        mapped_data = {
            meeting.id: {
                'total_capacity_reserved': total_capacity_reserved,
                'total_capacity_used': total_capacity_used,
            } for meeting, total_capacity_reserved, total_capacity_used in booking_data}

        for event in self:
            data = mapped_data.get(event.id)
            event.resource_total_capacity_reserved = data.get('total_capacity_reserved', 0) if data else 0
            event.resource_total_capacity_used = data.get('total_capacity_used', 0) if data else 0

    @api.depends('videocall_location', 'access_token')
    def _compute_videocall_redirection(self):
        for event in self:
            if not event.videocall_location:
                event.videocall_redirection = False
                continue
            if not event.access_token:
                event.access_token = uuid.uuid4().hex
            event.videocall_redirection = f"{self.get_base_url()}/calendar/videocall/{self.access_token}"

    @api.depends('appointment_type_id.event_videocall_source')
    def _compute_videocall_source(self):
        events_no_appointment = self.env['calendar.event']
        for event in self:
            if not event.appointment_type_id or event.videocall_location and not self.DISCUSS_ROUTE in event.videocall_location:
                events_no_appointment |= event
                continue
            event.videocall_source = event.appointment_type_id.event_videocall_source
        super(CalendarEvent, events_no_appointment)._compute_videocall_source()

    def _compute_is_highlighted(self):
        super(CalendarEvent, self)._compute_is_highlighted()
        if self.env.context.get('active_model') == 'appointment.type':
            appointment_type_id = self.env.context.get('active_id')
            for event in self:
                if event.appointment_type_id.id == appointment_type_id:
                    event.is_highlighted = True

    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows.
            Overridden here because we skip generating unique access tokens
            for potentially tons of existing event, should they be needed,
            they will be generated on the fly.
        """
        if column_name != 'access_token':
            super(CalendarEvent, self)._init_column(column_name)

    def _inverse_appointment_resource_id_or_capacity(self):
        """Update booking lines as inverse of both resource capacity and resource id.

        As both values are related to the booking line and resource capacity is dependant
        on resource id existing in the first place, They need to both use the same inverse
        field to ensure there is no ordering conflict.
        """
        for event in self:
            if not event.booking_line_ids and event.appointment_resource_id:
                self.env['appointment.booking.line'].sudo().create({
                    'appointment_resource_id': event.appointment_resource_id.id,
                    'calendar_event_id': event.id,
                    'capacity_reserved': event.resource_total_capacity_reserved,
                })
            elif len(event.booking_line_ids) == 1 and event.appointment_resource_id:
                event.booking_line_ids.appointment_resource_id = event.appointment_resource_id
                event.booking_line_ids.capacity_reserved = min(
                    event.resource_total_capacity_reserved or event.booking_line_ids.capacity_reserved,
                    event.appointment_resource_id.capacity
                )
            elif len(event.booking_line_ids) == 1:
                event.booking_line_ids.sudo().unlink()

    def _inverse_resource_ids_or_capacity(self):
        """Update booking lines as inverse of both resource capacity and resource_ids.

        As both values are related to the booking line and resource capacity is dependant
        on resources existing in the first place. They need to both use the same inverse
        field to ensure there is no ordering conflict.
        """
        booking_lines = []
        for event in self:
            resources = event.resource_ids
            if resources:
                if event.appointment_type_manage_capacity and self.resource_total_capacity_reserved:
                    capacity_to_reserve = self.resource_total_capacity_reserved
                else:
                    capacity_to_reserve = sum(event.booking_line_ids.mapped('capacity_reserved')) or sum(resources.mapped('capacity'))
                event.booking_line_ids.sudo().unlink()
                for resource in resources.sorted("shareable"):
                    if event.appointment_type_manage_capacity and capacity_to_reserve <= 0:
                        break
                    booking_lines.append({
                        'appointment_resource_id': resource.id,
                        'calendar_event_id': event.id,
                        'capacity_reserved': min(resource.capacity, capacity_to_reserve),
                    })
                    capacity_to_reserve -= min(resource.capacity, capacity_to_reserve)
                    capacity_to_reserve = max(0, capacity_to_reserve)
            else:
                event.booking_line_ids.sudo().unlink()
        self.env['appointment.booking.line'].sudo().create(booking_lines)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Simulate group_by on resource_ids by using appointment_resource_ids.
            appointment_resource_ids is only used to store the data through the appointment_booking_line
            table. All computation on the resources and the capacity reserved is done with capacity_reserved.
            Simulating the group_by on resource_ids also avoids to do weird override in JS on appointment_resource_ids.
            This is needed because when simply writing on the field, it tries to create the corresponding booking line
            with the field capacity_reserved required leading to ValidationError.
        """
        groupby = [group_element if group_element != "resource_ids" else "appointment_resource_ids" for group_element in groupby]
        read_group_data = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
        for data in read_group_data:
            if 'appointment_resource_ids' in data:
                data['resource_ids'] = data['appointment_resource_ids']
            if 'appointment_resource_ids_count' in data:
                data['resource_ids_count'] = data['appointment_resource_ids_count']
        return read_group_data

    def _read_group_appointment_resource_id(self, resources, domain, order):
        if not self.env.context.get('appointment_booking_gantt_show_all_resources'):
            return resources
        resources_domain = [
            '|', ('company_id', '=', False), ('company_id', 'in', self.env.context.get('allowed_company_ids', [])),
        ]
        # If we have a default appointment type, we only want to show those resources
        default_appointment_type = self.env.context.get('default_appointment_type_id')
        if default_appointment_type:
            return self.env['appointment.type'].browse(default_appointment_type).resource_ids.filtered_domain(resources_domain)
        return self.env['appointment.resource'].search(resources_domain)

    def _read_group_partner_ids(self, partners, domain, order):
        """Show the partners associated with relevant staff users in appointment gantt context."""
        if not self.env.context.get('appointment_booking_gantt_show_all_resources'):
            return partners
        appointment_type_id = self.env.context.get('default_appointment_type_id', False)
        appointment_types = self.env['appointment.type'].browse(appointment_type_id)
        if appointment_types:
            return appointment_types.staff_user_ids.partner_id
        return self.env['appointment.type'].search([('schedule_based_on', '=', 'users')]).staff_user_ids.partner_id

    def _read_group_user_id(self, users, domain, order):
        if not self.env.context.get('appointment_booking_gantt_show_all_resources'):
            return users
        appointment_types = self.env['appointment.type'].browse(self.env.context.get('default_appointment_type_id', []))
        if appointment_types:
            return appointment_types.staff_user_ids
        return self.env['appointment.type'].search([('schedule_based_on', '=', 'users')]).staff_user_ids

    def _track_filter_for_display(self, tracking_values):
        if self.appointment_type_id:
            return tracking_values.filtered(lambda t: t.field_id.name != 'active')
        return super()._track_filter_for_display(tracking_values)

    def _track_get_default_log_message(self, tracked_fields):
        if self.appointment_type_id and 'active' in tracked_fields:
            if self.active:
                return _('Appointment re-booked')
            else:
                return _("Appointment canceled")
        return super()._track_get_default_log_message(tracked_fields)

    def _generate_access_token(self):
        for event in self:
            event.access_token = self._default_access_token()

    def action_calendar_more_options(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action["views"] = [(False, 'form')]
        action["res_id"] = self.id
        return action

    def action_cancel_meeting(self, partner_ids):
        """ In case there are more than two attendees (responsible + another attendee),
            we do not want to archive the calendar.event.
            We'll just remove the attendee(s) that made the cancellation request
        """
        self.ensure_one()
        attendees = self.env['calendar.attendee'].search([('event_id', '=', self.id), ('partner_id', 'in', partner_ids)])
        if attendees:
            cancelling_attendees = ", ".join([attendee.display_name for attendee in attendees])
            message_body = _("Appointment canceled by: %(partners)s", partners=cancelling_attendees)
            if self.appointment_booker_id.id == partner_ids[0]:
                self._track_set_log_message(message_body)
                # Use the organizer if set or fallback on SUPERUSER to notify attendees that the event is archived
                self.with_user(self.user_id or SUPERUSER_ID).sudo().action_archive()
            else:
                # Use the organizer as the author if set or fallback on the first attendee cancelling
                author_id = self.user_id.partner_id.id or partner_ids[0]
                self.message_post(body=message_body, message_type='notification', author_id=author_id)
                self.partner_ids -= attendees.partner_id

    def _find_or_create_partners(self, guest_emails_str):
        """Used to find the partners from the emails strings and creates partners if not found.
        :param str guest_emails: optional line-separated guest emails. It will
          fetch or create partners to add them as event attendees;
        :return tuple: partners (recordset)"""
        # Split and normalize guest emails
        name_emails = email_split_tuples(guest_emails_str)
        emails_normalized = [email_normalize(email, strict=False) for _, email in name_emails]
        valid_normalized = set(filter(None, emails_normalized))  # uniquify, valid only
        partners = self.env['res.partner']
        if not valid_normalized:
            return partners
        # Find existing partners
        partners = self.env['mail.thread']._mail_find_partner_from_emails(list(valid_normalized))
        partners = self.env['res.partner'].concat(*partners)
        remaining_emails = valid_normalized - set(partners.mapped('email_normalized'))
        # limit public usage of guests
        if self.env.su and len(remaining_emails) > 10:
            raise ValueError(
                _('Guest usage is limited to 10 customers for performance reason.')
            )
        if remaining_emails:
            partner_values = [
                {'email': email, 'name': name if name else email}
                for name, email in name_emails
                if email in remaining_emails
            ]
            partners += self.env['res.partner'].create(partner_values)
        return partners

    def _get_mail_tz(self):
        self.ensure_one()
        if not self.event_tz and self.appointment_type_id.appointment_tz:
            return self.appointment_type_id.appointment_tz
        return super()._get_mail_tz()

    def _get_public_fields(self):
        return super()._get_public_fields() | {
            'appointment_resource_id',
            'appointment_resource_ids',
            'appointment_type_id',
            'resource_ids',
            'resource_total_capacity_reserved',
            'resource_total_capacity_used',
        }

    def _track_template(self, changes):
        res = super(CalendarEvent, self)._track_template(changes)
        if not self.appointment_type_id:
            return res

        appointment_type_sudo = self.appointment_type_id.sudo()
        # set 'author_id' and 'email_from' based on the organizer
        vals = {'author_id': self.user_id.partner_id.id, 'email_from': self.user_id.email_formatted} if self.user_id else {}

        if 'appointment_type_id' in changes:
            try:
                booked_template = self.env.ref('appointment.appointment_booked_mail_template')
            except ValueError as e:
                _logger.warning("Mail could not be sent, as mail template is not found : %s", e)
            else:
                res['appointment_type_id'] = (booked_template.sudo(), {
                    **vals,
                    'auto_delete_keep_log': False,
                    'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('appointment.mt_calendar_event_booked'),
                    'email_layout_xmlid': 'mail.mail_notification_light'
                })
        if (
            'active' in changes and not self.active and self.start > fields.Datetime.now()
            and appointment_type_sudo.canceled_mail_template_id
        ):
            res['active'] = (appointment_type_sudo.canceled_mail_template_id, {
                **vals,
                'auto_delete_keep_log': False,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('appointment.mt_calendar_event_canceled'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
        return res

    def _get_customer_description(self):
        # Description should make sense for the person who booked the meeting
        if self.appointment_type_id:
            message_confirmation = self.appointment_type_id.message_confirmation or ''
            contact_details = ''
            if self.partner_id and (self.partner_id.name or self.partner_id.email or self.partner_id.phone):
                email_detail_line = _('Email: %(email)s', email=self.partner_id.email) if self.partner_id.email else ''
                phone_detail_line = _('Phone: %(phone)s', phone=self.partner_id.phone) if self.partner_id.phone else ''
                contact_details = '\n'.join(line for line in (_('Contact Details:'), self.partner_id.name, email_detail_line, phone_detail_line) if line)
            return f"{html2plaintext(message_confirmation)}\n\n{contact_details}".strip()
        return super()._get_customer_description()

    def _get_customer_summary(self):
        # Summary should make sense for the person who booked the meeting
        if self.appointment_type_id and self.partner_id:
            return _('%(appointment_name)s with %(partner_name)s',
                     appointment_name=self.appointment_type_id.name,
                     partner_name=self.partner_id.name or _('somebody'))
        return super()._get_customer_summary()

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        # skip if not dealing with appointments
        resource_ids = [row['resId'] for row in rows if row.get('resId')]  # remove empty rows
        if not group_bys or group_bys[0] not in ('resource_ids', 'partner_ids') or not resource_ids:
            return super().gantt_unavailability(start_date, end_date, scale, group_bys=group_bys, rows=rows)

        start_datetime = fields.Datetime.from_string(start_date)
        end_datetime = fields.Datetime.from_string(end_date)
        start_datetime_utc = timezone_datetime(start_datetime)
        end_datetime_utc = timezone_datetime(end_datetime)

        # if viewing a specific appointment type generate unavailable intervals outside of the defined slots
        slots_unavailable_intervals = []
        appointment_type = self.env['appointment.type']
        if appointment_type_id := self.env.context.get('default_appointment_type_id'):
            appointment_type = appointment_type.browse(appointment_type_id)

        if appointment_type:
            slot_available_intervals = [
                (slot['utc'][0], slot['utc'][1])
                for slot in appointment_type._slots_generate(start_datetime_utc, end_datetime_utc, 'utc', reference_date=start_datetime_utc)
            ]
            slots_unavailable_intervals = invert_intervals(slot_available_intervals, start_datetime_utc, end_datetime_utc)

        # in staff view, add conflicting events to unavailabilities and return
        if group_bys[0] == 'partner_ids':
            unavailabilities = self._gantt_unavailabilities_events(start_datetime, end_datetime, self.env['res.partner'].browse(resource_ids))
            for row in rows:
                row_unavailabilities = unavailabilities.get(row['resId'], Intervals([]))
                row_unavailabilities |= Intervals([(start, stop, self.env['res.partner']) for start, stop in slots_unavailable_intervals])
                row['unavailabilities'] = [{'start': start, 'stop': stop} for start, stop, _ in row_unavailabilities]
            return rows

        appointment_resource_ids = self.env['appointment.resource'].browse(resource_ids)

        # in multi-company, if people can't access some of the resources we don't really care
        if self.env.context.get('allowed_company_ids'):
            appointment_resource_ids = appointment_resource_ids.filtered_domain([
                '|', ('company_id', '=', False), ('company_id', 'in', self.env.context['allowed_company_ids'])]
            )

        resource_unavailabilities = appointment_resource_ids.resource_id._get_unavailable_intervals(start_datetime, end_datetime)
        for row in rows:
            appointment_resource_id = appointment_resource_ids.browse(row.get('resId'))
            unavailabilities = Intervals([
                (start, stop, set())
                for start, stop in resource_unavailabilities.get(appointment_resource_id.resource_id.id, [])])
            unavailabilities |= Intervals([(start, stop, set()) for start, stop in slots_unavailable_intervals])
            row['unavailabilities'] = [{'start': start, 'stop': stop} for start, stop, _ in unavailabilities]
        return rows

    def _gantt_unavailabilities_events(self, start_datetime, end_datetime, partners):
        """Get a mapping from partner id to unavailabilities based on existing events.

        :return dict[int, Intervals[<res.partner>]]: {5: Intervals([(monday_morning, monday_noon, <res.partner>(5))])}
        """
        return {
            attendee.id: Intervals([
                (timezone_datetime(event.start), timezone_datetime(event.stop), attendee)
                for event in partners._get_calendar_events(start_datetime, end_datetime).get(attendee.id, [])
            ]) for attendee in partners
        }

    @api.model
    def get_gantt_data(self, domain, groupby, read_specification, limit=None, offset=0):
        """Filter out rows where the partner isn't linked to an staff user."""
        gantt_data = super().get_gantt_data(domain, groupby, read_specification, limit=limit, offset=offset)
        if self.env.context.get('appointment_booking_gantt_show_all_resources') and groupby and groupby[0] == 'partner_ids':
            staff_partner_ids = self.env['appointment.type'].search([('schedule_based_on', '=', 'users')]).staff_user_ids.partner_id.ids
            gantt_data['groups'] = [group for group in gantt_data['groups'] if group.get('partner_ids') and group['partner_ids'][0] in staff_partner_ids]
        return gantt_data
