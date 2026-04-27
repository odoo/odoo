# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar as cal
import pytz
import uuid

from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from ..tools.google_reserve_iap import GoogleReserveIAP


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    # field overrides
    assign_method = fields.Selection(compute="_compute_assign_method", store=True, readonly=False)

    # google reserve fields
    google_reserve_enable = fields.Boolean("Enable Google Booking")
    google_reserve_pending_sync = fields.Boolean("Google Booking Pending Synchronization", copy=False)
    google_reserve_merchant_id = fields.Many2one('google.reserve.merchant', string='Google Reserve Merchant',
                                                 help="Configure your company data for Google Reserve",
                                                 groups="appointment.group_appointment_manager")
    google_reserve_access_token = fields.Char('Google Reserve Access Token',
                                              default=lambda self: uuid.uuid4().hex,
                                              copy=False,
                                              groups="appointment.group_appointment_manager")

    @api.constrains('google_reserve_enable', 'category', 'assign_method')
    def _check_appointment_category_for_google_reserve(self):
        for appointment_type in self.filtered('google_reserve_enable'):
            if appointment_type.category in ('custom', 'punctual'):
                raise ValidationError(_(
                    "%(appointment_type_name)s: A %(appointment_category)s appointment type cannot be used with the Google Bookings integration.",
                    appointment_category=appointment_type.category,
                    appointment_type_name=appointment_type.name,
                ))
            if appointment_type.assign_method != 'time_auto_assign':
                raise ValidationError(_(
                    "%(appointment_type_name)s: The Google Bookings integration only works in the auto-assign mode.",
                    appointment_type_name=appointment_type.name,
                ))

    @api.constrains('google_reserve_enable', 'google_reserve_merchant_id')
    def _check_google_reserve_fields(self):
        for appointment_type in self.filtered('google_reserve_enable'):
            if not appointment_type.google_reserve_merchant_id:
                raise ValidationError(_(
                    "%(appointment_type_name)s: Please configure your Google Reserve Merchant for Google Reserve.",
                    appointment_type_name=appointment_type.name,
                ))

    @api.depends('google_reserve_enable')
    def _compute_assign_method(self):
        for appointment_type in self:
            if appointment_type.google_reserve_enable:
                appointment_type.assign_method = 'time_auto_assign'
            elif not appointment_type.assign_method:
                appointment_type.assign_method = 'resource_time'

    @api.model_create_multi
    def create(self, vals_list):
        """ Create corresponding merchants and services when appointment
        types with google_reserve_enable are created """

        appointment_types = super().create(vals_list)

        google_reserve_appointments = appointment_types.filtered('google_reserve_enable')
        if google_reserve_appointments and not self.env.user.has_group(
            'appointment.group_appointment_manager'
        ):
            raise AccessError(_('Only Appointment Managers can enable the Google Reserve Integration'))

        for appointment_type in google_reserve_appointments:
            GoogleReserveIAP().register_appointment(appointment_type)
        return appointment_types

    def write(self, values):
        """ Create/delete merchants and service base on the value of google_reserve_enable.
        Update the availabilities and service information if needed.
        """

        if not self.env.user.has_group('appointment.group_appointment_manager') and \
            'google_reserve_enable' in values:
            raise AccessError(_('Only Appointment Managers can enable or disable the Google Reserve Integration'))

        old_google_booking_appointments = self.filtered('google_reserve_enable')
        result = super().write(values)

        google_reserve_pending_sync = self.env['appointment.type']
        google_reserve_iap = GoogleReserveIAP()
        if 'google_reserve_enable' in values:
            if values['google_reserve_enable']:
                for appointment_type in self - old_google_booking_appointments:
                    google_reserve_iap.register_appointment(appointment_type)
                    google_reserve_pending_sync += appointment_type
            else:
                for appointment_type in old_google_booking_appointments:
                    google_reserve_iap.unregister_appointment(appointment_type)
        elif 'active' in values:
            for appointment_type in old_google_booking_appointments:
                google_reserve_pending_sync += appointment_type
                if values['active']:
                    google_reserve_iap.register_appointment(appointment_type)
                else:
                    google_reserve_iap.unregister_appointment(appointment_type)
        else:
            appointment_altering_values = {
                'name',
                'min_cancellation_hours',
                'min_schedule_hours',
            }

            slots_altering_values = {
                'min_cancellation_hours',
                'min_schedule_hours',
                'slot_ids',
                'staff_user_ids',
                'resource_ids',
                'appointment_duration',
            }

            google_booking_appointments = self.filtered('google_reserve_enable')
            for appointment_type in google_booking_appointments:
                if values.keys() & appointment_altering_values:
                    google_reserve_iap.register_appointment(appointment_type)
                    google_reserve_pending_sync += appointment_type

            if values.keys() & slots_altering_values:
                # we do not re-sync availabilities in this case as we would need to re-upload ALL
                # of them, instead we let the availabilities CRON feed run again the next day
                google_reserve_pending_sync += google_booking_appointments

        google_reserve_pending_sync.google_reserve_pending_sync = True

        return result

    @api.ondelete(at_uninstall=True)
    def _unlink_unregister_google_reserve(self):
        google_reserve_iap = GoogleReserveIAP()
        for appointment_type in self.filtered('google_reserve_enable'):
            google_reserve_iap.unregister_appointment(appointment_type)

    def action_google_reserve_enable(self):
        """ Linked to an action to have a button with a confirmation in form view. """
        self.google_reserve_enable = True

    def action_google_reserve_disable(self):
        """ Linked to an action to have a button with a confirmation in form view. """
        self.google_reserve_enable = False

    def _google_reserve_get_availabilities(self, start_time=False, end_time=False):
        """ Get the availabilities to send to the Google Reserve IAP service.

        Currently only working for appointment types in auto-assign mode.

        Example format of a specific availability: {
            "spots_total": 4,           # maximal number of reservations that can be made for this specific availability
            "spots_open": 3,            # number of reservations that can still be made for this availability
            "duration_sec": 3600,       # duration of the slot in seconds
            "start_sec": 12345678,      # starting time of the slot in UTC epoch time
            "resources": {              # resource info for the slot (can be used for user or resource) (opt)
                "party_size": 2,        # number of people the slot can take (opt)
            }
        }

        See: https://developers.google.com/actions-center/verticals/reservations/e2e/reference/feeds/availability-feed """

        self.ensure_one()
        availabilities = []
        if self.category in ('custom', 'punctual'):
            return availabilities

        if not start_time:
            start_time = datetime.now().astimezone(pytz.utc)

        if not end_time:
            # 30 days of coverage are needed for google
            max_schedule_days = max(30, self.max_schedule_days)
            # let's avoid spending more than 2 years of availabilities to keep perf under control
            max_schedule_days = min(730, self.max_schedule_days)
            end_time = datetime.combine(start_time + timedelta(days=max_schedule_days), time.max).astimezone(pytz.utc)

        slots = self._slots_generate(
            start_time + timedelta(hours=self.min_schedule_hours),
            end_time,
            'UTC',
            reference_date=start_time.replace(tzinfo=None),
        )

        if self.schedule_based_on == 'users':
            self.with_context(slots_check_all_users=True)._slots_fill_users_availability(
                slots,
                start_time,
                end_time,
            )

            availabilities = [
                self._google_reserve_format_slot_availabilities_users(slot)
                for slot in slots
            ]
        else:
            availability_values = self._slot_availability_prepare_resources_values(
                self.resource_ids, start_time + timedelta(hours=self.min_schedule_hours), end_time)

            for slot in slots:
                availabilities += self._google_reserve_format_slot_availabilities_resources(slot, availability_values)

        return availabilities

    def _google_reserve_format_slot_availabilities_users(self, slot):
        [start_utc, end_utc] = slot["UTC"]

        return {
            "spots_total": len(slot["slot"].restrict_to_user_ids or self.staff_user_ids),
            "spots_open": len(slot["available_staff_users"]) if "available_staff_users" in slot else 0,
            "duration_sec": int((end_utc - start_utc).total_seconds()),
            "start_sec": cal.timegm(start_utc.timetuple()),
        }

    def _google_reserve_format_slot_availabilities_resources(self, slot, availability_values):
        """ Compute and build the slot info for the availabilities of resources in Google's format.

        Google also wants to know how many spots would accommodate each capacity *regardless of bookings*.
        Meaning we send both the "theoretical" configuration where no-one has booked and the actual situation.

        Note: The maximum party-size defaults to 12 (somewhat arbitrary number previously used) and
        is now configurable via the appointment.resource_max_capacity_allowed system parameter.
        Keeping this value low has the big advantage of avoiding an explosion of the data size sent.
        Also, the upper limit is fixed to 20 due to Google Reserve max party size.

        (Overly simplified used case for demonstration).
        Considering a restaurant that has 2 tables of 2 spots, this will result in:
        [
            {"spots_open": 2, "spots_total": 2, "duration_sec": 3600, "start_sec": 1749819600, "resources": {"party_size": 1}},
            {"spots_open": 2, "spots_total": 2, "duration_sec": 3600, "start_sec": 1749819600, "resources": {"party_size": 2}},
        ]

        If we have a booking for one of the table, it becomes:
        [
            {"spots_open": 1, "spots_total": 2, "duration_sec": 3600, "start_sec": 1749819600, "resources": {"party_size": 1}},
            {"spots_open": 1, "spots_total": 2, "duration_sec": 3600, "start_sec": 1749819600, "resources": {"party_size": 2}},
        ]

        If both tables are "combinable" with each other, we get instead (without any bookings):
        [
            {"spots_open": 2, "spots_total": 2, "duration_sec": 3600, "start_sec": 1749819600, "resources": {"party_size": 1}},
            {"spots_open": 2, "spots_total": 2, "duration_sec": 3600, "start_sec": 1749819600, "resources": {"party_size": 2}},
            {"spots_open": 1, "spots_total": 1, "duration_sec": 3600, "start_sec": 1749819600, "resources": {"party_size": 3}},
            {"spots_open": 1, "spots_total": 1, "duration_sec": 3600, "start_sec": 1749819600, "resources": {"party_size": 4}},
        ]

        Technical notes:

        '_get_resources_remaining_capacity' returns a dict with appointment.resources as key AND a
        'total_remaining_capacity' key
        -> We manually exclude the 'total_remaining_capacity' entry as it makes processing the data
        more challenging and we do not need that information.

        When dealing with combinables, we have to keep track of what resources where used for
        what combinations, as the dict from '_get_resources_remaining_capacity' will return both:
        table 1: (table 1: capacity, table2: capacity)
        table 2: (table 1: capacity, table2: capacity)
        -> Those are the same combination, so it does not count as 'another available spot'.

        Meaning once a resource has been used for a certain combination for a certain capacity, it cannot
        be used again. """

        self.ensure_one()
        [start_utc, end_utc] = slot['UTC']

        remaining_capacity_by_resource = {
            resource: {
                appointment_resource: remaining_capacity
                for appointment_resource, remaining_capacity in self._get_resources_remaining_capacity(
                    resource,
                    start_utc,
                    end_utc,
                    resource_to_bookings=availability_values.get('resource_to_bookings'),
                ).items()
                if isinstance(appointment_resource, models.BaseModel)  # see docstring for explanations
            }
            for resource in self.resource_ids
        }

        availabilities = []
        allowed_max_capacity = int(self.env['ir.config_parameter'].sudo().get_param('appointment.resource_max_capacity_allowed', default=12))
        max_capacity = min(20, allowed_max_capacity, self.resource_total_capacity)  # see docstring
        for capacity in range(1, max_capacity + 1):

            # total numbers of resources that can accommodate this capacity, regardless of bookings
            used_resources = self.env['appointment.resource']
            total_spots = 0
            for resource, remaining_capacity in remaining_capacity_by_resource.items():
                accommodated_capacity = 0
                for resource in remaining_capacity:
                    if resource in used_resources:
                        continue

                    accommodated_capacity += resource.capacity
                    used_resources += resource
                    if accommodated_capacity >= capacity:
                        total_spots += 1
                        break

            if total_spots == 0:
                break

            # total numbers of resources that can accommodate this capacity, considering bookings
            # note: could theoretically be included in above loop but would be less readable and
            # is not very costly
            used_resources = self.env['appointment.resource']
            open_spots = 0
            for resource, remaining_capacity in remaining_capacity_by_resource.items():
                accommodated_capacity = 0

                for resource, remaining_capacity in remaining_capacity.items():
                    if resource in used_resources:
                        continue

                    accommodated_capacity += remaining_capacity
                    used_resources += resource
                    if accommodated_capacity >= capacity:
                        open_spots += 1
                        break

            availabilities.append({
                'spots_open': open_spots,
                'spots_total': total_spots,
                'duration_sec': int((end_utc - start_utc).total_seconds()),
                'start_sec': cal.timegm(start_utc.timetuple()),
                'resources': {
                    'party_size': capacity,
                },
            })

        return availabilities
