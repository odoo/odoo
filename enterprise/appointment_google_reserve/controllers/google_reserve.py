# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from datetime import datetime, timedelta
from werkzeug.exceptions import BadRequest, Forbidden

from odoo.http import Controller, request, route
from odoo.tools import consteq, email_normalize, hmac


class GoogleReserveController(Controller):

    @route('/appointment/<int:appointment_id>/<string:appointment_token>/google_reserve/availabilities',
           auth="public", methods=['GET'])
    def google_reserve_batch_availability_lookup(self, appointment_id, appointment_token):
        """ Route accessed by IAP to check the availabilities.

        The request data contains a list of slots to get availabilities from.
        Each of those slots are formatted as follows:
        {
            'start_sec': 1754466026  # UTC timestamp,
            'duration_sec': 3600  # Slot duration in seconds,
            'resources': {
                'party_size': 4  # The requested party-size, what we usually call 'capacity' in Odoo
            }
        }

        It has to return a list with each given slot along with a boolean flag "available".

        See full documentation for details:
        https://developers.google.com/actions-center/verticals/reservations/e2e/reference/booking-server-api-rest/e2e-methods/batchavailabilitylookup-method?hl=en """

        slot_time = request.get_json_data()  # not compatible with JSON-RPC, manually fetch params
        if not slot_time:
            raise BadRequest("Invalid JSON payload")

        appointment_type_su = self._fetch_appointment(appointment_id, appointment_token)

        slot_time_availability = []
        min_date = datetime.fromtimestamp(int(slot_time[0]['start_sec']), tz=pytz.UTC)
        max_date = min_date + timedelta(seconds=int(slot_time[0]['duration_sec']))
        for slot in slot_time:
            slot_start = datetime.fromtimestamp(int(slot['start_sec']), tz=pytz.UTC)
            slot_stop = slot_start + timedelta(seconds=int(slot['duration_sec']))

            if slot_start < min_date:
                min_date = slot_start
            if slot_stop > max_date:
                max_date = slot_stop

        availabilities = appointment_type_su._google_reserve_get_availabilities(start_time=min_date, end_time=max_date)
        for slot in slot_time:
            slot_time_availability.append({
                "available": any((
                    (
                        not slot.get('resource_ids') or
                        (slot.get('resource_ids') and slot['resource_ids'].get('party_size') and a['resources']['party_size'] >= slot['resource_ids']['party_size'])
                    ) and
                    a['start_sec'] == int(slot['start_sec']) and
                    a['duration_sec'] == int(slot['duration_sec']) and
                    a['spots_open'] >= 1)
                    for a in availabilities),
                "slot_time": slot,
            })

        return request.make_json_response(slot_time_availability)

    @route('/appointment/<int:appointment_id>/<string:appointment_token>/google_reserve/booking/create',
           auth="public", methods=['POST'], csrf=False)
    def google_reserve_booking_create(self, appointment_id, appointment_token):
        """ Route accessed by Google (through IAP) when a booking needs to be created.

        Format of Google provided information:
        {
            'idempotency_token': 'token1',
            'slot': {
                'confirmation_mode': 'CONFIRMATION_MODE_SYNCHRONOUS',
                'duration_sec': '3600',
                'merchant_id': 1,
                'resources': {
                    'party_size': '4',
                },
                'service_id': 1,
                'start_sec': 1644850800,
            },
            'user_information': {
                'email': 'john.doe@test.com',
                'family_name': 'Doe',
                'given_name': 'John',
                'telephone': '+32476112233',
                'user_id': '1234567890',
            }
        }

        Global flow:

        1. Generate slots

        Generate slots based on desired slot time and capacity (party_size).
        This only generates a single slot as the duration we receive from Google matches the
        appointment duration.
        (Note: 'party_size' param is only provided for resources-based appointments)

        2. Fill slots availability

        Fill our single slot with availabilities for users or resources.
        This will re-use the existing appointment logic and account for time-off, pick the best
        resource to accommodate the desired party size, etc.

        3. Create the booking

        Based on information extracted from the generated slot and the booker information provided
        by Google, we create the calendar.event record.

        We re-use '_prepare_calendar_event_values' here as the flow is very similar to what we do
        when booking from the Odoo front-end.

        4. Return the response with Google's format.

        See: https://developers.google.com/actions-center/verticals/reservations/e2e/reference/booking-server-api-rest/e2e-methods/createbooking-method

        Technical note:

        We force the access_token of the created calendar.event manually by using the provided
        idempotency_token from Google.
        This allows us to identify the booking without having to store yet another field. """

        route_params = request.get_json_data()  # not compatible with JSON-RPC, manually fetch params

        if not all(bool(route_params.get(key)) for key in [
            'idempotency_token', 'user_information', 'slot'
        ]):
            raise BadRequest("Invalid JSON payload")

        appointment_type_su = self._fetch_appointment(appointment_id, appointment_token)
        slot_info = route_params['slot']
        user_info = route_params['user_information']

        token = hmac(
            request.env(su=True),
            "appointment-google-reserve-create-booking",
            (appointment_type_su.id, route_params['idempotency_token'])
        )[:36]
        calendar_event = request.env['calendar.event'].sudo().search([('access_token', '=', token)])
        if calendar_event:
            # booking already created, shortcut the method
            return request.make_json_response({
                'booking': {
                    'booking_id': str(calendar_event.id),
                    'status': 'CONFIRMED',
                    'slot': slot_info,
                    'user_information': user_info,
                }
            })

        duration_sec = int(slot_info['duration_sec'])
        start_sec = int(slot_info['start_sec'])
        stop_sec = start_sec + duration_sec
        start_slot = datetime.fromtimestamp(start_sec)
        stop_slot = datetime.fromtimestamp(stop_sec)

        party_size = 0
        if 'resources' in slot_info and 'party_size' in slot_info['resources']:
            party_size = int(slot_info['resources']['party_size'])

        generated_slots = appointment_type_su._slots_generate(
            start_slot.astimezone(pytz.utc),
            stop_slot.astimezone(pytz.utc),
            'UTC',
        )
        selected_slot = next((
            slot for slot in generated_slots
            if slot['UTC'][0] == start_slot and slot['UTC'][1] == stop_slot), None)
        slots_to_fill = [selected_slot] if selected_slot else []

        if appointment_type_su.schedule_based_on == 'users':
            appointment_type_su._slots_fill_users_availability(
                slots_to_fill,
                start_slot.astimezone(pytz.utc),
                stop_slot.astimezone(pytz.utc),
            )
        else:
            appointment_type_su._slots_fill_resources_availability(
                slots_to_fill,
                start_slot.astimezone(pytz.utc),
                stop_slot.astimezone(pytz.utc),
                asked_capacity=party_size,
            )

        slot = slots_to_fill[0] if slots_to_fill else False

        staff_user = request.env['res.users']
        booking_lines = []
        booking_response = False
        if appointment_type_su.schedule_based_on == 'resources' and slot and 'available_resource_ids' in slot:
            resources = slot['available_resource_ids']
            resources_remaining_capacity = appointment_type_su._get_resources_remaining_capacity(
                resources,
                start_slot,
                stop_slot,
                with_linked_resources=False
            )

            booking_lines = []
            capacity_to_assign = party_size
            for resource in resources:
                resource_remaining_capacity = resources_remaining_capacity.get(resource)
                new_capacity_reserved = min(resource_remaining_capacity, capacity_to_assign, resource.capacity)
                capacity_to_assign -= new_capacity_reserved
                booking_lines.append({
                    'appointment_resource_id': resource.id,
                    'capacity_reserved': new_capacity_reserved,
                    'capacity_used': new_capacity_reserved if resource.shareable and appointment_type_su.resource_manage_capacity else
                        resource.capacity if appointment_type_su.resource_manage_capacity else 1,
                })
        elif appointment_type_su.schedule_based_on == 'users' and slot and ('available_staff_users' in slot or 'staff_user_id' in slot):
            staff_user = slot.get('available_staff_users', [False])[0] or slot['staff_user_id']

        if booking_lines or staff_user:
            customer_email = email_normalize(user_info['email'])
            customer = request.env['mail.thread'].sudo()._mail_find_partner_from_emails(
                [customer_email],
                force_create=True
            )
            if customer:
                customer = customer[0]
            else:
                raise BadRequest('Invalid Email')

            if 'telephone' in user_info:
                customer_phone = customer._phone_format(number=user_info['telephone']) or user_info['telephone']
                if customer.phone_sanitized != customer_phone:
                    customer.phone = user_info['telephone']

            appointment_values = appointment_type_su._prepare_calendar_event_values(
                asked_capacity=party_size,
                booking_line_values=booking_lines,
                duration=duration_sec / 3600,
                appointment_invite=request.env['appointment.invite'],
                guests=None,
                name=customer.name,
                customer=customer,
                staff_user=staff_user,
                start=start_slot,
                stop=stop_slot,
            )

            calendar_event = request.env['calendar.event'].sudo().create({
                **appointment_values,
                'access_token': token,
                'is_google_reserve': True,
            })

            booking_response = {
                'booking': {
                    'booking_id': str(calendar_event.id),
                    'status': 'CONFIRMED',
                    'slot': slot_info,
                    'user_information': user_info,
                }
            }
        else:
            booking_response = {
                'booking': {
                    'booking_id': False,
                    'status': 'FAILED',
                    'slot': slot_info,
                    'user_information': user_info,
                },
                'booking_failure': {
                    'cause': 'SLOT_UNAVAILABLE',
                }
            }

        return request.make_json_response(booking_response)

    @route('/appointment/<int:appointment_id>/<string:appointment_token>/google_reserve/booking/<int:calendar_event_id>/update',
           auth="public", methods=['POST'], csrf=False)
    def google_reserve_booking_update(self, appointment_id, appointment_token, calendar_event_id):
        """ Route accessed by Google (through IAP) when a booking needs to be updated.

        Format of Google provided information:
        {
            'booking': {
                'booking_id': '42',  # matches calendar.event record ID
                'slot': {
                    'resources': {
                        'duration_sec': '3600',
                        'start_sec': 1644850800,
                        'party_size': 11,
                    },
                },
            }
        }

        RESOURCES BOOKINGS -> 3 cases

        1. Modify date and party_size

        We generate the slot to find suitable resources, similarly to what is done in
        'google_reserve_booking_create'.

        If we have available resources, we then modify the values of 'resource_ids' and
        'resource_total_capacity_reserved' and let the inverse method fix the booking lines, see
        'calendar.event#_inverse_resource_ids_or_capacity'.

        2. Modify the party_size only

        We fetch the booking lines related to our calendar.event.
        If there is only 1 booking line and the resource can accommodate the capacity, we only alter
        the 'resource_total_capacity_reserved' and keep the same resources.

        Otherwise, meaning we ask more capacity than the resource can accommodate or we already have
        multiple booking lines (typically for shared resources), the code fallbacks to use case 1 to
        try to find another suitable slot.

        3. Modify dates only

        We try to keep the same resource as the initial booking and verify its availability using
        '_check_appointment_is_valid_slot'.
        If it's available -> great, otherwise fallback to use case 1 to try to find another suitable
        slot.

        STAFF BOOKINGS -> 1 case

        It is much simpler for staff bookings as only the date can be modified.
        We check if it's available using '_check_appointment_is_valid_slot' and if not we simply
        return to Google with an availability error, we do not try to find another staff user as it
        would be rather complex: have to cancel the initial meeting or adapt the attendees, what
        about notifications, etc.

        We may consider adding support for this in the future but resources bookings (restaurants)
        are our main target currently.

        Once the calendar.event has been modified (or if we don't have availabilities), we return
        a response with Google's format.

        See: https://developers.google.com/actions-center/verticals/reservations/e2e/reference/booking-server-api-rest/e2e-methods/updatebooking-method """

        route_params = request.get_json_data()  # not compatible with JSON-RPC, manually fetch params

        if not route_params.get('booking'):
            raise BadRequest("Invalid JSON payload")

        appointment_type_su = self._fetch_appointment(appointment_id, appointment_token)
        calendar_event = request.env['calendar.event'].sudo().with_context(
            active_test=False,
        ).search([
            ('id', '=', calendar_event_id),
            ('appointment_type_id', '=', appointment_type_su.id)
        ])

        if not calendar_event:
            raise BadRequest("Unknown Booking")

        booking_info = route_params['booking']

        booking_response = {}
        failure_status = False
        if booking_info.get('status') == 'CANCELED':
            if not calendar_event.active:
                failure_status = 'BOOKING_ALREADY_CANCELLED'
            else:
                calendar_event.with_context(google_reserve_service_rpc=True).action_archive()
                booking_response = {
                    'booking': booking_info,
                }
        elif 'slot' in booking_info:
            calendar_event_vals = {
                'start': calendar_event.start,
                'duration': calendar_event.duration,
            }

            resources_booking = appointment_type_su.schedule_based_on == 'resources'
            modifying_dates = 'start_sec' in booking_info['slot'] and 'duration_sec' in booking_info['slot']
            modifying_party_size = 'resources' in booking_info['slot'] and 'party_size' in booking_info['slot']['resources']

            if modifying_dates:
                # try to simply move the date while keeping the same resources / staff user
                calendar_event_vals.update({
                    'start': datetime.fromtimestamp(int(booking_info['slot']['start_sec'])),
                    'duration': int(booking_info['slot']['duration_sec']) / 3600,
                })

                if not calendar_event.with_context(
                    ignore_event_ids=calendar_event.ids
                ).appointment_type_id._check_appointment_is_valid_slot(
                    staff_user=calendar_event.partner_id.user_ids[0]
                        if not resources_booking and calendar_event.partner_id.user_ids else False,
                    resources=calendar_event.appointment_resource_ids,
                    asked_capacity=calendar_event.resource_total_capacity_reserved,
                    timezone='UTC',
                    start_dt=calendar_event_vals['start'].astimezone(pytz.utc),
                    duration=calendar_event_vals['duration'],
                ):
                    if resources_booking and not modifying_party_size:
                        # the same resources are not available with the new dates
                        # -> force re-computing party size to try with new resources
                        booking_info['slot'].update({
                            'resources': {
                                'party_size': calendar_event.resource_total_capacity_reserved
                            }
                        })
                        modifying_party_size = True
                    elif not resources_booking:
                        # staff user is not available -> we currently do not support trying to find
                        # someone else instead as it would require cancelling meetings which would
                        # in turn notify Google, it would also be confusing for meeting organization
                        failure_status = 'SLOT_UNAVAILABLE'

            if resources_booking and modifying_party_size:
                old_party_size = calendar_event.resource_total_capacity_reserved
                new_party_size = int(booking_info['slot']['resources']['party_size'])
                booking_lines = calendar_event.booking_line_ids
                if not modifying_dates and len(booking_lines) == 1 and (
                    new_party_size <= max(old_party_size, booking_lines.appointment_resource_id.capacity)
                ):
                    # when a single booking line and capacity allows -> just adapt capacity
                    calendar_event_vals['resource_total_capacity_reserved'] = new_party_size
                else:
                    # otherwise re-generate the slot to find available resources to accommodate it
                    start_dt_utc = calendar_event_vals['start'].astimezone(pytz.utc)
                    stop_dt_utc = start_dt_utc + timedelta(hours=calendar_event_vals['duration'])
                    slots = calendar_event.appointment_type_id._slots_generate(start_dt_utc, stop_dt_utc, 'UTC')
                    slots = [slot for slot in slots if slot['UTC'][0] == start_dt_utc.replace(tzinfo=None) and slot['UTC'][1] == stop_dt_utc.replace(tzinfo=None)]
                    calendar_event.with_context(
                        ignore_event_ids=calendar_event.ids
                    ).appointment_type_id._slots_fill_resources_availability(
                        slots,
                        start_dt_utc,
                        stop_dt_utc,
                        asked_capacity=new_party_size,
                    )
                    if slots and slots[0].get('available_resource_ids'):
                        calendar_event_vals.update({
                            'resource_ids': slots[0]['available_resource_ids'],
                            'resource_total_capacity_reserved': new_party_size,
                        })
                    elif modifying_dates:
                        failure_status = 'SLOT_UNAVAILABLE'
                    else:
                        failure_status = 'USER_OVER_BOOKING_LIMIT'

            if not failure_status:
                calendar_event.with_context(google_reserve_service_rpc=True).write(calendar_event_vals)

                booking_response = {
                    'booking': dict(
                        booking_info,
                        status='CONFIRMED',
                        payment_information={'prepayment_status': 'PREPAYMENT_NOT_PROVIDED'},
                    ),
                }

                booking_response['booking']['slot']['resources'] = {
                    'party_size': str(calendar_event.resource_total_capacity_reserved)
                }

        if failure_status:
            booking_response = {
                'booking': {
                    'booking_id': str(calendar_event.id),
                    'status': 'FAILED',
                },
                'booking_failure': {
                    'cause': failure_status,
                }
            }

        return request.make_json_response(booking_response)

    @route('/appointment/google_reserve/upload_availabilities_feed',
           auth="public", methods=['POST'], csrf=False)
    def google_reserve_upload_availabilities_feed(self):
        route_params = request.get_json_data()  # not compatible with JSON-RPC, manually fetch params

        google_reserve_access_token_pairs = route_params.get('google_reserve_access_token_pairs')
        if not google_reserve_access_token_pairs or not isinstance(google_reserve_access_token_pairs, list):
            raise Forbidden()

        for google_reserve_access_token_pair in google_reserve_access_token_pairs:
            appointment_type = request.env['appointment.type'].sudo().search([
                ('id', '=', google_reserve_access_token_pair['appointment_type_id']),
                ('google_reserve_enable', '=', True)
            ])

            if not appointment_type or not consteq(
                appointment_type.google_reserve_access_token,
                google_reserve_access_token_pair['appointment_token']
            ):
                raise Forbidden()

        request.env.ref('appointment_google_reserve.ir_cron_iap_google_reserve_availabilities')._trigger()

    # --------------------------------------
    # UTILS
    # --------------------------------------

    def _fetch_appointment(self, appointment_id, appointment_token):
        if not appointment_id or not appointment_token:
            raise BadRequest("Unknown Appointment")

        appointment_type = request.env['appointment.type'].sudo().search([
            ('id', '=', appointment_id),
            ('google_reserve_enable', '=', True)
        ])

        if not appointment_type or not consteq(
            appointment_type.google_reserve_access_token, appointment_token):
            raise BadRequest("Unknown Appointment")

        return appointment_type
