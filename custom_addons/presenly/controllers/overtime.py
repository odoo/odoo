from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class PresenlyOvertimeController(http.Controller):
    def _payload(self, params):
        if not isinstance(params, dict):
            raise ValidationError('JSON-RPC params must be a JSON object.')
        return params

    def _employee(self):
        employee = request.env.user.employee_id
        if not employee or not employee.active:
            raise UserError('The authenticated user has no active employee.')
        return employee

    def _overtime_day(self, payload):
        """Return the overtime date string from ``date`` (or legacy ``date_from``)."""
        date_value = payload.get('date') or payload.get('date_from')
        if date_value:
            return fields.Date.to_string(fields.Date.to_date(date_value))
        return False

    def _overtime_hour(self, value, default=None):
        """Parse a 24h hour value (float, int, or 'HH:MM').

        Returns ``None`` when the value is absent so callers can distinguish
        'missing' from a valid midnight hour (``0``/``0.0``).
        """
        if value in (None, ''):
            return default
        try:
            if isinstance(value, str) and ':' in value:
                parts = value.split(':')
                return float(parts[0]) + float(parts[1]) / 60.0
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError('Overtime hours must be valid 24h values.')

    def _location(self, employee, payload):
        """Resolve the work location for the overtime day.

        - Explicit ``work_location_id`` -> validated against the day.
        - Omitted -> auto-resolve a unique location for the day (K2/first slot);
          ambiguous/multi-location day is rejected with per-date detail (K1).
        """
        location_id = payload.get('work_location_id') or payload.get('unit_id')
        date = self._overtime_day(payload)
        if not date:
            raise ValidationError('date is required.')
        if location_id in (None, ''):
            location, by_date, ambiguous, error = employee._presenly_resolve_period_location(
                date, date,
            )
            if error:
                raise ValidationError(error)
            if ambiguous:
                details = ', '.join(
                    f'{day} -> {entry["name"] or "no location"}'
                    for day, entry in by_date.items()
                )
                raise ValidationError(
                    'The requested period covers more than one Work Location'
                    f' ({details}). Pick one explicitly.'
                )
            if not location:
                raise ValidationError(
                    'No Work Location is configured for the requested period.'
                )
            return location
        try:
            location = request.env['hr.work.location'].browse(int(location_id)).exists()
        except (TypeError, ValueError) as error:
            raise ValidationError('work_location_id must be numeric when provided.') from error
        scheduled = employee._presenly_work_locations_for_period(date, date)
        if (
            not location
            or not location.active
            or location.company_id != employee.company_id
            or location not in scheduled
        ):
            raise ValidationError(
                'The Work Location must be scheduled for the employee during the requested period.'
            )
        return location

    def _serialize(self, overtime):
        approval = overtime.presenly_approval_request_id
        current_approvers = approval.current_approver_ids if approval else request.env['res.users']
        return {
            'id': overtime.id,
            'name': overtime.display_name,
            'employee_id': overtime.employee_id.id,
            'company_id': overtime.company_id.id,
            'work_location_id': overtime.work_location_id.id or False,
            'date': overtime.date,
            'hour_from': overtime.hour_from,
            'hour_to': overtime.hour_to,
            'duration_hours': overtime.duration_hours,
            'reason': overtime.reason,
            'has_attendance_evidence': overtime.has_attendance_evidence,
            'state': overtime.state,
            'approval_level': overtime.approval_level,
            'approval_progress': approval.progress_display if approval else False,
            'current_approvers': [
                {'id': user.id, 'name': user.name} for user in current_approvers
            ],
            'approval_steps': [{
                'level': step.level,
                'name': step.name,
                'state': step.state,
                'approver_ids': step.assigned_user_ids.ids,
                'decision_by': step.decision_user_id.name or False,
                'decision_date': step.decision_date or False,
                'decision_note': step.decision_note or False,
            } for step in approval.step_ids] if approval else [],
            'rejection_reason': overtime.rejection_reason,
        }

    @http.route(
        '/api/presenly/v1/overtime/requests',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def create(self, **params):
        employee = self._employee()
        payload = self._payload(params)
        location = self._location(employee, payload)
        date = self._overtime_day(payload)
        hour_from = self._overtime_hour(payload.get('hour_from'))
        hour_to = self._overtime_hour(payload.get('hour_to'))
        if not date:
            raise ValidationError('date is required.')
        if hour_from is None or hour_to is None:
            raise ValidationError('hour_from and hour_to are required.')
        try:
            overtime = request.env['presenly.overtime.request'].create({
                'employee_id': employee.id,
                'work_location_id': location.id,
                'date': date,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'reason': payload.get('reason') or '',
            })
        except KeyError as error:
            raise ValidationError(f'Missing required field: {error.args[0]}.') from error
        overtime.action_submit()
        return {'success': True, 'data': self._serialize(overtime), 'error': None}

    @http.route(
        '/api/presenly/v1/overtime/requests/list',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def list(self):
        employee = self._employee()
        records = request.env['presenly.overtime.request'].search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=100)
        return {
            'success': True,
            'data': [self._serialize(item) for item in records],
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/overtime/requests/approval',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def approval_queue(self):
        employee = self._employee()
        records = request.env['presenly.overtime.request'].search([
            ('state', '=', 'submitted'),
            ('company_id', '=', employee.company_id.id),
        ], order='create_date desc', limit=100)
        records = records.filtered(
            lambda item: request.env.user in item._presenly_pending_approver_users()
        )
        return {
            'success': True,
            'data': [self._serialize(item) for item in records],
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/overtime/requests/<int:overtime_id>/approve',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def approve(self, overtime_id):
        overtime = request.env['presenly.overtime.request'].browse(overtime_id).exists()
        if not overtime:
            raise ValidationError('Overtime request not found.')
        overtime.action_presenly_approve()
        return {'success': True, 'data': self._serialize(overtime), 'error': None}

    @http.route(
        '/api/presenly/v1/overtime/requests/<int:overtime_id>/reject',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def reject(self, overtime_id, **params):
        overtime = request.env['presenly.overtime.request'].browse(overtime_id).exists()
        reason = self._payload(params).get('reason')
        if not overtime or not reason:
            raise ValidationError('Overtime request and rejection reason are required.')
        overtime.action_presenly_reject(reason)
        return {'success': True, 'data': self._serialize(overtime), 'error': None}

    @http.route(
        '/api/presenly/v1/overtime/requests/<int:overtime_id>/cancel',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def cancel(self, overtime_id):
        overtime = request.env['presenly.overtime.request'].browse(overtime_id).exists()
        if not overtime:
            raise ValidationError('Overtime request not found.')
        overtime.action_cancel()
        return {'success': True, 'data': self._serialize(overtime), 'error': None}

    @http.route(
        '/api/presenly/v1/overtime/requests/<int:overtime_id>/can-approve',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def can_approve(self, overtime_id):
        overtime = request.env['presenly.overtime.request'].browse(overtime_id).exists()
        if not overtime:
            raise ValidationError('Overtime request not found.')
        return {
            'success': True,
            'data': {
                'id': overtime.id,
                'state': overtime.state,
                'approval_progress': self._serialize(overtime)['approval_progress'],
                'current_approvers': self._serialize(overtime)['current_approvers'],
                'can_approve': overtime.presenly_can_approve_api,
                'can_reject': overtime.presenly_can_reject_api,
                'can_cancel': overtime.presenly_can_cancel_api,
            },
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/overtime/requests/can-approve/batch',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def can_approve_batch(self, **params):
        payload = self._payload(params)
        raw_ids = payload.get('ids')
        if not isinstance(raw_ids, list) or not raw_ids:
            raise ValidationError('ids must be a non-empty list of Overtime request IDs.')
        try:
            ids = [int(item) for item in raw_ids]
        except (TypeError, ValueError):
            raise ValidationError('ids must contain only numeric Overtime request IDs.')
        records = request.env['presenly.overtime.request'].search([('id', 'in', ids)])
        return {
            'success': True,
            'data': {
                'items': [{
                    'id': overtime.id,
                    'state': overtime.state,
                    'approval_progress': self._serialize(overtime)['approval_progress'],
                    'current_approvers': self._serialize(overtime)['current_approvers'],
                    'can_approve': overtime.presenly_can_approve_api,
                    'can_reject': overtime.presenly_can_reject_api,
                    'can_cancel': overtime.presenly_can_cancel_api,
                } for overtime in records],
                'unreadable_ids': [item for item in ids if item not in records.ids],
            },
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/overtime/requests/location-options',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def location_options(self, **params):
        employee = self._employee()
        payload = self._payload(params)
        date = payload.get('date')
        if not date:
            raise ValidationError('date is required.')
        location, by_date, ambiguous, error = employee._presenly_resolve_period_location(
            date, date,
        )
        if error:
            raise ValidationError(error)
        locations = sorted(
            {entry['id']: entry['name'] for entry in by_date.values()
             if entry['id']}.items(),
        )
        return {
            'success': True,
            'data': {
                'unique': not ambiguous and bool(location),
                'location_id': location.id or False,
                'locations': [
                    {'id': item_id, 'name': name}
                    for item_id, name in locations
                ],
                'by_date': by_date,
            },
            'error': None,
        }