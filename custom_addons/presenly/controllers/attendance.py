import hashlib
import math

from odoo import SUPERUSER_ID, api, fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.modules.registry import Registry


class PresenlyAttendanceController(http.Controller):
    def _response(self, success, data=None, error=None):
        return {'success': success, 'data': data or {}, 'error': error}

    def _employee(self):
        employee = request.env.user.employee_id
        if not employee or not employee.active:
            raise UserError('The authenticated user has no active employee.')
        if employee.company_id not in request.env.companies:
            raise UserError(
                'The employee company is not available in the authenticated user Allowed Companies.'
            )
        return employee

    def _payload(self, payload):
        if not isinstance(payload, dict):
            raise ValidationError('JSON-RPC params must be a JSON object.')
        return payload

    def _failed(self, employee, event_type, payload, error):
        # The business transaction is rolled back after the exception. Use a
        # separate cursor so failed-attempt evidence remains durable. Selfie
        # bytes and raw device identifiers are never copied to the failed log.
        registry = Registry(request.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['presenly.attendance.event'].create_failed_event(
                env['hr.employee'].browse(employee.id), event_type, payload, str(error),
            )
            cr.commit()
        raise error

    def _device_id_hash(self, payload):
        device_id = payload.get('device_id')
        if device_id in (None, ''):
            return False
        if not isinstance(device_id, str):
            raise ValidationError('device_id must be text when provided.')
        device_id = device_id.strip()
        if not device_id or len(device_id) > 255:
            raise ValidationError('device_id must contain between 1 and 255 characters.')
        return hashlib.sha256(device_id.encode('utf-8')).hexdigest()

    def _location_data(self, location, schedule=False):
        return {
            'id': location.id,
            'name': location.name,
            'schedule_id': schedule.id or False,
            'geofence_ready': location.presenly_is_geofence_ready,
            'geofence_radius_meters': location.presenly_radius_meters,
            'gps_accuracy_limit_meters': (
                location.presenly_gps_accuracy_limit_meters
            ),
            'require_selfie_check_in': (
                location.presenly_require_selfie_check_in
            ),
            'require_selfie_check_out': (
                location.presenly_require_selfie_check_out
            ),
        }

    def _location_for_employee(self, employee, latitude, longitude, accuracy, payload):
        locations, schedules = employee._presenly_locations_at()
        requested_id = payload.get('work_location_id')
        # unit_id remains a temporary compatibility alias for older clients.
        if requested_id in (None, ''):
            requested_id = payload.get('unit_id')
        if requested_id not in (None, ''):
            try:
                requested_id = int(requested_id)
            except (TypeError, ValueError) as error:
                raise ValidationError(
                    'work_location_id must be a numeric value.'
                ) from error
            locations = locations.filtered(lambda location: location.id == requested_id)
            schedules = schedules.filtered(
                lambda schedule: schedule.work_location_id.id == requested_id
            )
            if not locations:
                raise ValidationError(
                    'The selected Work Location is not scheduled at this time.'
                )
        if not locations:
            raise ValidationError(
                'There is no Work Location scheduled for the current time.'
            )
        for location in locations.sorted(lambda item: item.id):
            if location.is_coordinate_allowed(latitude, longitude, accuracy):
                schedule = schedules.filtered(
                    lambda item: item.work_location_id == location
                )[:1]
                return location, schedule
        if all(not location.presenly_is_geofence_ready for location in locations):
            raise ValidationError(
                'The scheduled Work Location is not ready for geofence attendance.'
            )
        if all(
            accuracy > location.presenly_gps_accuracy_limit_meters
            for location in locations.filtered('presenly_is_geofence_ready')
        ):
            raise ValidationError(
                'GPS accuracy is outside the allowed limit for the scheduled Work Location.'
            )
        raise ValidationError(
            'Your position is outside the scheduled Work Location geofence.'
        )

    def _validate_coordinates(self, payload):
        try:
            latitude = float(payload['latitude'])
            longitude = float(payload['longitude'])
            accuracy = float(payload['accuracy'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError(
                'latitude, longitude, and accuracy are required numeric values.'
            ) from error
        if not all(math.isfinite(value) for value in (latitude, longitude, accuracy)):
            raise ValidationError('GPS values must be finite numeric values.')
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValidationError('Coordinates are outside the valid range.')
        if accuracy <= 0:
            raise ValidationError('accuracy must be greater than zero meters.')
        return latitude, longitude, accuracy

    def _optional_coordinates(self, payload):
        """Return (None, None, None) or validate any provided GPS values."""
        raw_latitude = payload.get('latitude')
        raw_longitude = payload.get('longitude')
        raw_accuracy = payload.get('accuracy')
        if raw_latitude in (None, '') and raw_longitude in (None, '') and raw_accuracy in (None, ''):
            return None, None, None
        return self._validate_coordinates(payload)

    def _selfie(self, payload, required=True):
        selfie = payload.get('selfie')
        if required and not selfie:
            raise ValidationError('selfie is required for this attendance event.')
        if not selfie:
            return False
        # Validation is centralized in the evidence model and also repeated
        # during attachment creation to keep non-controller callers safe.
        request.env['presenly.attendance.event'].validate_selfie(selfie)
        return selfie

    def _requested_mode(self, payload):
        """Map the mobile 'mode'/'attendance_mode' value to a server mode.

        WFA is informational for now: no geofence, no location requirement,
        and no approval. The controller still owns identity and timestamps.
        """
        value = payload.get('attendance_mode')
        if value in (None, ''):
            value = payload.get('mode')
        if value in (None, ''):
            return 'location'
        if not isinstance(value, str):
            raise ValidationError('attendance_mode must be text.')
        normalized = value.strip().lower().replace('_', '-')
        if normalized in ('wfa', 'work-from-anywhere'):
            return 'wfa'
        if normalized in ('location', 'on-site', 'onsite', 'on', 'office'):
            return 'location'
        raise ValidationError(
            'attendance_mode must be either "location" or "wfa".'
        )

    @http.route(
        '/api/presenly/v1/attendance/modes',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def modes(self):
        employee = self._employee()
        return self._response(True, {
            'employee_id': employee.id,
            'company_id': employee.company_id.id,
            'available_modes': [
                {
                    'mode': 'location',
                    'label': 'On-Site',
                    'requires_gps': True,
                    'requires_work_location': True,
                    'requires_selfie': 'per_location_policy',
                },
                {
                    'mode': 'wfa',
                    'label': 'Work From Anywhere',
                    'requires_gps': False,
                    'requires_work_location': False,
                    'requires_selfie': True,
                },
            ],
            'default_mode': 'location',
            'wfa_policy': {
                'allowed': True,
                'approval_required': False,
                'geofence_required': False,
                'time_or_location_limit': False,
                'selfie_required': True,
            },
        })

    @http.route(
        '/api/presenly/v1/attendance/status',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def status(self):
        employee = self._employee()
        attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id), ('check_out', '=', False),
        ], order='check_in desc', limit=1)

        if attendance:
            locations = attendance.presenly_work_location_id
            schedules = attendance.presenly_schedule_id
        else:
            locations, schedules = employee._presenly_locations_at()

        available_locations = []
        for location in locations.sorted(lambda item: item.id):
            schedule = schedules.filtered(
                lambda item: item.work_location_id == location
            )[:1]
            available_locations.append(self._location_data(location, schedule))

        location = attendance.presenly_work_location_id
        ready_locations = locations.filtered('presenly_is_geofence_ready')
        wfa_available = True
        if attendance:
            attendance_message = 'Employee has an active attendance session.'
        elif not locations:
            attendance_message = (
                'No Work Location is scheduled; Work From Anywhere is available.'
                if wfa_available else 'No Work Location is scheduled for the current time.'
            )
        elif not ready_locations:
            attendance_message = (
                'The scheduled Work Location is not geofence-ready; '
                'Work From Anywhere is available.'
                if wfa_available else 'The scheduled Work Location is not geofence-ready.'
            )
        else:
            attendance_message = 'Employee is ready to check in.'

        # Auto-selection guidance for the mobile client.
        unique_locations = locations.filtered('presenly_is_geofence_ready')
        recommended_id = False
        ambiguous = False
        if unique_locations:
            if len(unique_locations) == 1:
                recommended_id = unique_locations.id or False
            else:
                ambiguous = True

        return self._response(True, {
            'server_time': fields.Datetime.now(),
            'employee_id': employee.id,
            'employee_name': employee.name,
            'company_id': employee.company_id.id,
            'company_name': employee.company_id.name,
            'state': 'checked_in' if attendance else 'checked_out',
            'can_check_in': not attendance and (bool(ready_locations) or wfa_available),
            'can_check_out': bool(attendance),
            'message': attendance_message,
            'attendance_id': attendance.id or False,
            'check_in': attendance.check_in or False,
            'work_location_id': location.id or False,
            'work_location_name': location.name or False,
            'schedule_id': attendance.presenly_schedule_id.id or False,
            'attendance_mode': attendance.presenly_attendance_mode or False,
            'available_work_locations': available_locations,
            'recommended_work_location_id': recommended_id,
            'auto_selection_supported': bool(ready_locations),
            'ambiguous': ambiguous,
            'can_select_mode': True,
            'wfa_available': wfa_available,
        })

    @http.route(
        '/api/presenly/v1/attendance/check-in',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def check_in(self, **params):
        employee = self._employee()
        payload = self._payload(params)
        try:
            attendance_model = request.env['hr.attendance'].sudo()
            if attendance_model.search_count([
                ('employee_id', '=', employee.id), ('check_out', '=', False),
            ]):
                raise UserError('Employee is already checked in.')
            mode = self._requested_mode(payload)
            device_id_hash = self._device_id_hash(payload)
            event_model = request.env['presenly.attendance.event']

            if mode == 'wfa':
                # Informational WFA: no geofence and no location requirement.
                # A selfie is still mandatory for identity/evidence; GPS is
                # optional. No approval is created for this temporary mode.
                selfie = self._selfie(payload, required=True)
                latitude, longitude, accuracy = self._optional_coordinates(payload)
                location = request.env['hr.work.location'].sudo()
                schedule = request.env['presenly.work.location.schedule'].sudo()
                attachment = event_model.create_selfie_attachment(
                    employee, selfie, 'check_in'
                ) if selfie else request.env['ir.attachment']
                attendance = attendance_model._presenly_mobile_create({
                    'employee_id': employee.id,
                    'presenly_company_id': employee.company_id.id,
                    'presenly_source': 'mobile',
                    'presenly_attendance_mode': 'wfa',
                    'presenly_selfie_in_attachment_id': attachment.id,
                    'in_mode': 'technical',
                    'in_latitude': latitude or False,
                    'in_longitude': longitude or False,
                })
            else:
                latitude, longitude, accuracy = self._validate_coordinates(payload)
                location, schedule = self._location_for_employee(
                    employee, latitude, longitude, accuracy, payload,
                )
                selfie = self._selfie(
                    payload, required=location.presenly_require_selfie_check_in,
                )
                distance = location._haversine_distance_meters(
                    location.latitude, location.longitude, latitude, longitude,
                )
                attachment = event_model.create_selfie_attachment(
                    employee, selfie, 'check_in'
                ) if selfie else request.env['ir.attachment']
                attendance = attendance_model._presenly_mobile_create({
                    'employee_id': employee.id,
                    'presenly_company_id': employee.company_id.id,
                    'presenly_work_location_id': location.id,
                    'presenly_schedule_id': schedule.id,
                    'presenly_check_in_distance': distance,
                    'presenly_selfie_in_attachment_id': attachment.id,
                    'presenly_source': 'mobile',
                    'presenly_attendance_mode': 'location',
                    'in_latitude': latitude,
                    'in_longitude': longitude,
                    'in_mode': 'technical',
                })

            event = event_model.create({
                'employee_id': employee.id,
                'attendance_id': attendance.id,
                'event_type': 'check_in',
                'latitude': latitude or False,
                'longitude': longitude or False,
                'accuracy': accuracy or 0.0,
                'distance_from_location': (
                    location._haversine_distance_meters(
                        location.latitude, location.longitude, latitude, longitude,
                    ) if mode == 'location' else False
                ),
                'work_location_id': (
                    location.id if mode == 'location' else False
                ),
                'schedule_id': schedule.id if mode == 'location' and schedule else False,
                'attendance_mode': mode,
                'selfie_attachment_id': attachment.id,
                'source': 'mobile',
                'validation_status': 'success',
                'device_id_hash': device_id_hash,
            })
            if attachment:
                attachment.write({
                    'res_model': 'presenly.attendance.event', 'res_id': event.id,
                })
            return self._response(True, {
                'attendance_id': attendance.id,
                'event_id': event.id,
                'state': 'checked_in',
                'check_in': attendance.check_in,
                'company_id': employee.company_id.id,
                'attendance_mode': mode,
                'work_location_id': (
                    attendance.presenly_work_location_id.id or False
                ),
                'work_location_name': (
                    attendance.presenly_work_location_id.name or False
                ),
                'schedule_id': attendance.presenly_schedule_id.id or False,
                'validation': {
                    'status': 'success',
                    'mode': mode,
                    'geofence_valid': mode == 'location',
                    'distance_meters': (
                        round(attendance.presenly_check_in_distance, 2)
                        if mode == 'location' else False
                    ),
                    'accuracy_meters': accuracy,
                    'selfie_received': bool(attachment),
                },
            })
        except (UserError, ValidationError) as error:
            self._failed(employee, 'check_in', payload, error)

    @http.route(
        '/api/presenly/v1/attendance/check-out',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def check_out(self, **params):
        employee = self._employee()
        payload = self._payload(params)
        try:
            attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id), ('check_out', '=', False),
            ], order='check_in desc', limit=1)
            if not attendance:
                raise UserError('Employee has no active check-in.')

            mode = attendance.presenly_attendance_mode or 'location'
            location = attendance.presenly_work_location_id
            event_model = request.env['presenly.attendance.event']

            if mode == 'wfa':
                # WFA checkout is informational: no geofence and no
                # same-location constraint. A selfie is still mandatory;
                # GPS remains optional.
                latitude, longitude, accuracy = self._optional_coordinates(payload)
                selfie = self._selfie(payload, required=True)
                attachment = event_model.create_selfie_attachment(
                    employee, selfie, 'check_out'
                ) if selfie else request.env['ir.attachment']
            else:
                latitude, longitude, accuracy = self._validate_coordinates(payload)
                requested_id = payload.get('work_location_id')
                if requested_id in (None, ''):
                    requested_id = payload.get('unit_id')
                if requested_id not in (None, ''):
                    try:
                        if int(requested_id) != location.id:
                            raise ValidationError(
                                'Check-out must use the same work location as check-in.'
                            )
                    except (TypeError, ValueError) as error:
                        raise ValidationError(
                            'work_location_id must be a numeric value.'
                        ) from error
                if not location:
                    raise ValidationError(
                        'The active attendance has no Work Location snapshot.'
                    )
                if not location.presenly_is_geofence_ready:
                    raise ValidationError(
                        'The check-in Work Location is not ready for geofence attendance.'
                    )
                if accuracy > location.presenly_gps_accuracy_limit_meters:
                    raise ValidationError(
                        'GPS accuracy is outside the allowed limit for the check-in Work Location.'
                    )
                if not location.is_coordinate_allowed(latitude, longitude, accuracy):
                    raise ValidationError(
                        'Check-out must be performed at the same allowed Work Location as check-in.'
                    )
                selfie = self._selfie(
                    payload, required=location.presenly_require_selfie_check_out,
                )
                attachment = event_model.create_selfie_attachment(
                    employee, selfie, 'check_out'
                ) if selfie else request.env['ir.attachment']

            device_id_hash = self._device_id_hash(payload)
            distance = location._haversine_distance_meters(
                location.latitude, location.longitude, latitude, longitude,
            ) if mode == 'location' else False
            attendance._presenly_mobile_checkout({
                'check_out': fields.Datetime.now(),
                'presenly_check_out_distance': distance,
                'presenly_selfie_out_attachment_id': attachment.id,
                'out_latitude': latitude,
                'out_longitude': longitude,
                'out_mode': 'technical',
            })
            event = event_model.create({
                'employee_id': employee.id,
                'attendance_id': attendance.id,
                'event_type': 'check_out',
                'latitude': latitude or False,
                'longitude': longitude or False,
                'accuracy': accuracy or 0.0,
                'distance_from_location': distance or False,
                'work_location_id': (
                    location.id if mode == 'location' else False
                ),
                'schedule_id': attendance.presenly_schedule_id.id,
                'attendance_mode': mode,
                'selfie_attachment_id': attachment.id,
                'source': 'mobile',
                'validation_status': 'success',
                'device_id_hash': device_id_hash,
            })
            if attachment:
                attachment.write({
                    'res_model': 'presenly.attendance.event', 'res_id': event.id,
                })
            return self._response(True, {
                'attendance_id': attendance.id,
                'event_id': event.id,
                'state': 'checked_out',
                'check_in': attendance.check_in,
                'check_out': attendance.check_out,
                'worked_hours': attendance.worked_hours,
                'company_id': employee.company_id.id,
                'attendance_mode': mode,
                'work_location_id': (
                    attendance.presenly_work_location_id.id or False
                ),
                'work_location_name': (
                    attendance.presenly_work_location_id.name or False
                ),
                'schedule_id': attendance.presenly_schedule_id.id or False,
                'validation': {
                    'status': 'success',
                    'mode': mode,
                    'geofence_valid': mode == 'location',
                    'same_work_location': mode == 'location',
                    'distance_meters': (
                        round(attendance.presenly_check_out_distance, 2)
                        if mode == 'location' else False
                    ),
                    'accuracy_meters': accuracy,
                    'selfie_received': bool(attachment),
                },
            })
        except (UserError, ValidationError) as error:
            self._failed(employee, 'check_out', payload, error)
