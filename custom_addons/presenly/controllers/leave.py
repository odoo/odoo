from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

class PresenlyLeaveController(http.Controller):
    def _payload(self, params):
        if not isinstance(params, dict):
            raise ValidationError('JSON-RPC params must be a JSON object.')
        return params

    def _employee(self):
        employee = request.env.user.employee_id
        if not employee or not employee.active:
            raise UserError('The authenticated user has no active employee.')
        return employee

    def _work_location(self, employee, payload):
        """Validate an explicit Work Location against the request period.

        Fallback: when ``work_location_id`` is missing, auto-resolve ONE
        location for the whole period via ``_presenly_resolve_period_location``:
        - unique -> use it;
        - ambiguous (multi-location period) -> raise with the per-date detail (K1);
        - no location -> raise.
        """
        date_from = payload.get('date_from')
        date_to = payload.get('date_to', date_from)
        location_id = payload.get('work_location_id') or payload.get('unit_id')
        if location_id in (None, ''):
            location, by_date, ambiguous, error = employee._presenly_resolve_period_location(
                date_from, date_to,
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
        scheduled_locations = employee._presenly_work_locations_for_period(
            date_from, date_to,
        ) if date_from else request.env['hr.work.location']
        if (
            not location
            or not location.active
            or location.company_id != employee.company_id
            or location not in scheduled_locations
        ):
            raise ValidationError(
                'The Work Location must be scheduled for the employee during the requested period.'
            )
        return location

    def _serialize(self, leave):
        location_id = leave.presenly_work_location_id.id or False
        approval = leave.presenly_approval_request_id
        current_approvers = approval.current_approver_ids if approval else request.env['res.users']
        return {
            'id': leave.id,
            'name': leave.display_name,
            'employee_id': leave.employee_id.id,
            'company_id': leave.company_id.id,
            'leave_type_id': leave.holiday_status_id.id,
            'leave_type': leave.holiday_status_id.name,
            # Compatibility: unit_id now aliases native work_location_id.
            'unit_id': location_id,
            'work_location_id': location_id,
            'date_from': leave.request_date_from,
            'date_to': leave.request_date_to,
            'number_of_days': leave.number_of_days,
            'state': leave.state,
            'approval_state': leave.presenly_approval_state,
            'approval_level': leave.presenly_approval_level,
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
            'rejection_reason': leave.presenly_rejection_reason,
        }

    @http.route(
        '/api/presenly/v1/leave/types',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def leave_types(self):
        employee = self._employee()
        types = request.env['hr.leave.type'].search([
            '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
            ('active', '=', True),
        ], order='sequence, name')
        return {
            'success': True,
            'data': [{'id': item.id, 'name': item.name} for item in types],
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/leaves',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def create_leave(self, **params):
        employee = self._employee()
        payload = self._payload(params)
        try:
            leave_type = request.env['hr.leave.type'].browse(
                int(payload['leave_type_id'])
            ).exists()
            location = self._work_location(employee, payload)
            if (
                not leave_type
                or (leave_type.company_id and leave_type.company_id != employee.company_id)
            ):
                raise ValidationError('Invalid Time Off type for this company.')
            leave = request.env['hr.leave'].create({
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'presenly_work_location_id': location.id,
                'request_date_from': payload['date_from'],
                'request_date_to': payload.get('date_to', payload['date_from']),
                'name': payload.get('reason') or 'Leave request',
            })
            # Presenly remains the only approval path and snapshots its levels
            # before any native validation runs.
            leave.action_presenly_submit()
            return {'success': True, 'data': self._serialize(leave), 'error': None}
        except (KeyError, TypeError, ValueError, UserError, ValidationError) as error:
            raise ValidationError(str(error)) from error

    @http.route(
        '/api/presenly/v1/leaves/approval',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def approval_queue(self):
        employee = self._employee()
        candidates = request.env['hr.leave'].search([
            ('presenly_approval_state', '=', 'pending'),
            ('company_id', '=', employee.company_id.id),
        ], order='create_date desc', limit=100)
        leaves = candidates.filtered(
            lambda leave: request.env.user in leave._presenly_pending_approver_users()
        )
        return {
            'success': True,
            'data': [self._serialize(leave) for leave in leaves],
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/leaves/list',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def leaves_list(self):
        employee = self._employee()
        records = request.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=100)
        return {
            'success': True,
            'data': [self._serialize(leave) for leave in records],
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/leaves',
        type='jsonrpc', auth='user', methods=['GET'],
    )
    def leaves(self):
        # Backward compatibility: mobile should use POST /leaves/list.
        return self.leaves_list()

    @http.route(
        '/api/presenly/v1/leaves/<int:leave_id>/approve',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def approve(self, leave_id):
        leave = request.env['hr.leave'].browse(leave_id).exists()
        if not leave:
            raise ValidationError('Leave request not found.')
        leave.action_presenly_approve()
        return {'success': True, 'data': self._serialize(leave), 'error': None}

    @http.route(
        '/api/presenly/v1/leaves/<int:leave_id>/reject',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def reject(self, leave_id, **params):
        reason = self._payload(params).get('reason')
        if not reason:
            raise ValidationError('A rejection reason is required.')
        leave = request.env['hr.leave'].browse(leave_id).exists()
        if not leave:
            raise ValidationError('Leave request not found.')
        leave.action_presenly_reject(reason)
        return {'success': True, 'data': self._serialize(leave), 'error': None}

    @http.route(
        '/api/presenly/v1/leaves/<int:leave_id>/can-approve',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def can_approve(self, leave_id):
        """Check whether the authenticated user can approve/reject/cancel this
        Time Off request at the current level.

        Batched capability check for a mobile approval screen: individual
        approve/reject rights follow the active approval step, cancel follows
        ownership/manager rights.
        """
        leave = request.env['hr.leave'].browse(leave_id).exists()
        if not leave:
            raise ValidationError('Leave request not found.')
        return {
            'success': True,
            'data': {
                'id': leave.id,
                'approval_state': leave.presenly_approval_state,
                'approval_progress': self._serialize(leave)['approval_progress'],
                'current_approvers': self._serialize(leave)['current_approvers'],
                'can_approve': leave.presenly_can_approve_api,
                'can_reject': leave.presenly_can_reject_api,
                'can_cancel': leave.presenly_can_cancel_api,
            },
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/leaves/can-approve/batch',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def can_approve_batch(self, **params):
        """Batched variant: check a list of Time Off requests at once.

        Body: ``params: { "ids": [44, 45] }``. Items are always returned for
        the IDs the caller is allowed to read; access to records outside the
        allowed companies is silently omitted.
        """
        payload = self._payload(params)
        raw_ids = payload.get('ids')
        if not isinstance(raw_ids, list) or not raw_ids:
            raise ValidationError('ids must be a non-empty list of Time Off request IDs.')
        try:
            ids = [int(item) for item in raw_ids]
        except (TypeError, ValueError):
            raise ValidationError('ids must contain only numeric Time Off request IDs.')
        records = request.env['hr.leave'].search(
            [('id', 'in', ids)],
        )
        return {
            'success': True,
            'data': {
                'items': [{
                    'id': leave.id,
                    'approval_state': leave.presenly_approval_state,
                    'approval_progress': self._serialize(leave)['approval_progress'],
                    'current_approvers': self._serialize(leave)['current_approvers'],
                    'can_approve': leave.presenly_can_approve_api,
                    'can_reject': leave.presenly_can_reject_api,
                    'can_cancel': leave.presenly_can_cancel_api,
                } for leave in records],
                'unreadable_ids': [item for item in ids if item not in records.ids],
            },
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/leaves/location-options',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def location_options(self, **params):
        """Preview the auto-resolved Work Location for a Time Off period.

        Body: ``params: { "date_from": ..., "date_to": ... }``. Returns the
        unique recommended location when the whole period maps to one location;
        otherwise marks ``unique=false`` and returns the per-date breakdown so
        the mobile can either pick explicitly or adjust the dates.
        """
        employee = self._employee()
        payload = self._payload(params)
        date_from = payload.get('date_from')
        date_to = payload.get('date_to', date_from)
        if not date_from:
            raise ValidationError('date_from is required.')
        location, by_date, ambiguous, error = employee._presenly_resolve_period_location(
            date_from, date_to,
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