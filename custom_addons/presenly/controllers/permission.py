from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


class PresenlyPermissionController(http.Controller):
    def _employee(self):
        employee = request.env.user.employee_id
        if not employee or not employee.active:
            raise ValidationError('The authenticated user has no active employee.')
        return employee

    def _payload(self, params):
        if not isinstance(params, dict):
            raise ValidationError('JSON-RPC params must be a JSON object.')
        return params

    def _work_location(self, employee, payload):
        """Validate an explicit Work Location against the request period.

        Fallback: when ``work_location_id`` is missing, auto-resolve ONE
        location for the whole period:
        - full_day: K2 (first slot per day);
        - hours: K2b (slot overlapping the requested hours, fallback first);
        - unique -> use it;
        - ambiguous (multi-location period) -> raise with per-date detail (K1);
        - no location -> raise.
        """
        date_from = payload.get('date_from')
        date_to = payload.get('date_to', date_from)
        location_id = payload.get('work_location_id') or payload.get('unit_id')
        if location_id in (None, ''):
            hour_from = payload.get('hour_from')
            hour_to = payload.get('hour_to')
            kwargs = {}
            if hour_from not in (None, ''):
                kwargs['hour_from'] = hour_from
                kwargs['hour_to'] = hour_to if hour_to not in (None, '') else hour_from
            location, by_date, ambiguous, error = employee._presenly_resolve_period_location(
                date_from, date_to, **kwargs,
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

    def _serialize(self, permission):
        location_id = permission.work_location_id.id or False
        approval = permission.presenly_approval_request_id
        current_approvers = approval.current_approver_ids if approval else request.env['res.users']
        return {
            'id': permission.id,
            'name': permission.display_name,
            'employee_id': permission.employee_id.id,
            'company_id': permission.company_id.id,
            # Compatibility: unit_id now aliases native work_location_id.
            'unit_id': location_id,
            'work_location_id': location_id,
            'permission_type_id': permission.permission_type_id.id,
            'permission_type': permission.permission_type_id.name,
            'request_mode': permission.request_mode,
            'date_from': permission.date_from,
            'date_to': permission.date_to,
            'hour_from': permission.hour_from,
            'hour_to': permission.hour_to,
            'reason': permission.reason,
            'state': permission.state,
            'approval_level': permission.approval_level,
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
            'rejection_reason': permission.rejection_reason,
            'affects_attendance': permission.affects_attendance,
            'paid_status': permission.paid_status,
            'attachments': [
                {'id': item.id, 'name': item.name, 'mimetype': item.mimetype}
                for item in permission.attachment_ids
            ],
        }

    @http.route(
        '/api/presenly/v1/permissions/types',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def types(self):
        employee = self._employee()
        records = request.env['presenly.permission.type'].search([
            ('company_id', '=', employee.company_id.id),
            ('active', '=', True),
            ('is_complete', '=', True),
        ], order='sequence, name')
        return {
            'success': True,
            'data': [{
                'id': item.id,
                'name': item.name,
                'code': item.code,
                'requires_attachment': item.requires_attachment,
            } for item in records],
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/permissions',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def create(self, **params):
        employee = self._employee()
        payload = self._payload(params)
        location = self._work_location(employee, payload)
        try:
            permission_type_id = int(payload['permission_type_id'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError('permission_type_id is required and must be numeric.') from error
        permission_type = request.env['presenly.permission.type'].browse(
            permission_type_id
        ).exists()
        if (
            not permission_type
            or not permission_type.active
            or not permission_type.is_complete
            or permission_type.company_id != employee.company_id
        ):
            raise ValidationError('Invalid or incomplete permission type.')
        try:
            permission = request.env['presenly.permission'].create({
                'employee_id': employee.id,
                'work_location_id': location.id,
                'permission_type_id': permission_type.id,
                'request_mode': payload.get('request_mode', 'full_day'),
                'date_from': payload['date_from'],
                'date_to': payload.get('date_to', payload['date_from']),
                'hour_from': payload.get('hour_from', 0),
                'hour_to': payload.get('hour_to', 0),
                'reason': payload['reason'],
            })
        except KeyError as error:
            raise ValidationError(f'Missing required field: {error.args[0]}.') from error
        request.env['presenly.permission'].create_api_attachments(
            permission, payload.get('attachments', []),
        )
        permission.action_submit()
        return {'success': True, 'data': self._serialize(permission), 'error': None}

    @http.route(
        '/api/presenly/v1/permissions',
        type='jsonrpc', auth='user', methods=['GET'],
    )
    def list(self):
        return self.permissions_list()

    @http.route(
        '/api/presenly/v1/permissions/list',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def permissions_list(self):
        employee = self._employee()
        records = request.env['presenly.permission'].search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=100)
        return {
            'success': True,
            'data': [self._serialize(item) for item in records],
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/permissions/approval',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def approval_queue(self):
        employee = self._employee()
        records = request.env['presenly.permission'].search([
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
        '/api/presenly/v1/permissions/<int:permission_id>/approve',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def approve(self, permission_id):
        permission = request.env['presenly.permission'].browse(permission_id).exists()
        if not permission:
            raise ValidationError('Permission request not found.')
        permission.action_approve()
        return {'success': True, 'data': self._serialize(permission), 'error': None}

    @http.route(
        '/api/presenly/v1/permissions/<int:permission_id>/reject',
        type='jsonrpc', auth='user', methods=['POST'],
    )
    def reject(self, permission_id, **params):
        permission = request.env['presenly.permission'].browse(permission_id).exists()
        reason = self._payload(params).get('reason')
        if not permission or not reason:
            raise ValidationError(
                'Permission request and rejection reason are required.'
            )
        permission.action_reject(reason)
        return {'success': True, 'data': self._serialize(permission), 'error': None}

    @http.route(
        '/api/presenly/v1/permissions/<int:permission_id>/can-approve',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def can_approve(self, permission_id):
        """Check whether the authenticated user can approve/reject/cancel this
        Permission request at the current level.

        Batched capability check for a mobile approval screen: individual
        approve/reject rights follow the active approval step, cancel follows
        ownership/manager rights.
        """
        permission = request.env['presenly.permission'].browse(permission_id).exists()
        if not permission:
            raise ValidationError('Permission request not found.')
        return {
            'success': True,
            'data': {
                'id': permission.id,
                'state': permission.state,
                'approval_progress': self._serialize(permission)['approval_progress'],
                'current_approvers': self._serialize(permission)['current_approvers'],
                'can_approve': permission.presenly_can_approve_api,
                'can_reject': permission.presenly_can_reject_api,
                'can_cancel': permission.presenly_can_cancel_api,
            },
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/permissions/can-approve/batch',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def can_approve_batch(self, **params):
        """Batched variant: check a list of Permission requests at once.

        Body: ``params: { "ids": [33, 34] }``. Items are always returned for
        the IDs the caller is allowed to read; access to records outside the
        allowed companies is silently omitted.
        """
        payload = self._payload(params)
        raw_ids = payload.get('ids')
        if not isinstance(raw_ids, list) or not raw_ids:
            raise ValidationError('ids must be a non-empty list of Permission request IDs.')
        try:
            ids = [int(item) for item in raw_ids]
        except (TypeError, ValueError):
            raise ValidationError('ids must contain only numeric Permission request IDs.')
        records = request.env['presenly.permission'].search(
            [('id', 'in', ids)],
        )
        return {
            'success': True,
            'data': {
                'items': [{
                    'id': permission.id,
                    'state': permission.state,
                    'approval_progress': self._serialize(permission)['approval_progress'],
                    'current_approvers': self._serialize(permission)['current_approvers'],
                    'can_approve': permission.presenly_can_approve_api,
                    'can_reject': permission.presenly_can_reject_api,
                    'can_cancel': permission.presenly_can_cancel_api,
                } for permission in records],
                'unreadable_ids': [item for item in ids if item not in records.ids],
            },
            'error': None,
        }

    @http.route(
        '/api/presenly/v1/permissions/location-options',
        type='jsonrpc', auth='user', methods=['POST'], readonly=True,
    )
    def location_options(self, **params):
        """Preview the auto-resolved Work Location for a Permission period.

        Body: ``params: { "date_from", "date_to", "request_mode?",
        "hour_from"?, "hour_to"? }``. Returns the unique recommended location
        when the whole period maps to one location; otherwise marks
        ``unique=false`` and returns the per-date breakdown so the mobile can
        either pick explicitly or adjust the dates.
        """
        employee = self._employee()
        payload = self._payload(params)
        date_from = payload.get('date_from')
        date_to = payload.get('date_to', date_from)
        if not date_from:
            raise ValidationError('date_from is required.')
        mode = payload.get('request_mode', 'full_day')
        kwargs = {}
        if mode == 'hours':
            hour_from = payload.get('hour_from')
            hour_to = payload.get('hour_to')
            if hour_from not in (None, ''):
                kwargs['hour_from'] = hour_from
                kwargs['hour_to'] = hour_to if hour_to not in (None, '') else hour_from
        location, by_date, ambiguous, error = employee._presenly_resolve_period_location(
            date_from, date_to, **kwargs,
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
