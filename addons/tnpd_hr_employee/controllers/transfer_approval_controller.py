# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

import json
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Hard cap on records returned per page.
_MAX_LIMIT = 100


class TransferApprovalController(http.Controller):

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def _json_response(self, data, status=200):
        """Return a JSON HTTP response with the correct Content-Type header."""
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _ok(self, message, **extra):
        payload = {'success': True, 'message': message}
        payload.update(extra)
        return self._json_response(payload)

    def _err(self, message, status=400):
        return self._json_response({'success': False, 'message': message}, status=status)

    def _parse_json_body(self):
        """
        Parse the request body as JSON.
        Returns (data_dict, None) on success or (None, error_response) on failure.
        """
        try:
            data = json.loads(request.httprequest.data or '{}')
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object at the top level.')
            return data, None
        except (json.JSONDecodeError, ValueError) as exc:
            return None, self._err(f'Invalid JSON body: {exc}')

    # ------------------------------------------------------------------
    # Shared business logic
    # ------------------------------------------------------------------

    def _format_request(self, rec):
        """Serialize a transfer.approval.request browse record for API responses."""

        def _m2o(field):
            return field.name if field else ''

        return {
            'request_id': rec.id,
            'employee_id': rec.employee_id.id,
            'employee_name': rec.employee_id.name or '',
            'current_central_prison': _m2o(rec.current_central_prison),
            'current_district_jail': _m2o(rec.current_district_jail),
            'current_sub_jail': _m2o(rec.current_sub_jail),
            'requested_central_prison': _m2o(rec.requested_central_prison),
            'requested_district_jail': _m2o(rec.requested_district_jail),
            'requested_sub_jail': _m2o(rec.requested_sub_jail),
            'state': rec.state,
            'requested_by': rec.requested_by.name or '',
            'approval_user': _m2o(rec.approval_user_id),
            'approved_by': rec.approved_by.name or '',
            'approved_date': str(rec.approved_date) if rec.approved_date else '',
            'remarks': rec.remarks or '',
            'create_date': str(rec.create_date) if rec.create_date else '',
        }

    # ------------------------------------------------------------------
    # API 1 – Create Transfer Approval Request
    # POST /api/transfer/save-approval-request
    # ------------------------------------------------------------------

    @http.route(
        '/api/transfer/save-approval-request',
        auth='user',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def save_approval_request(self, **_kwargs):
        """
        Create a new transfer approval request.

        Body (JSON)
        -----------
        employee_id             int  required
        requested_central_prison int  required  (tnpd.prison.master id, type=central)
        requested_district_jail  int  required  (tnpd.prison.master id, type=district)
        requested_sub_jail       int  required  (tnpd.prison.master id, type=sub)
        approval_user_id        int  required
        remarks                 str  optional
        """
        try:
            data, err = self._parse_json_body()
            if err:
                return err

            # --- Required field presence ------------------------------------
            required = [
                'employee_id',
                'requested_central_prison',
                'requested_district_jail',
                'requested_sub_jail',
                'approval_user_id',
            ]
            missing = [f for f in required if not data.get(f)]
            if missing:
                return self._err(f'Missing required fields: {", ".join(missing)}')

            env = request.env

            # --- Validate employee ------------------------------------------
            employee = env['hr.employee'].sudo().browse(int(data['employee_id']))
            if not employee.exists():
                return self._err('Employee not found', status=404)

            # --- Validate approval user -------------------------------------
            approval_user = env['res.users'].sudo().browse(int(data['approval_user_id']))
            if not approval_user.exists():
                return self._err('Approval user not found', status=404)

            # --- Validate requested prison records --------------------------
            PrisonMaster = env['tnpd.prison.master'].sudo()

            central = PrisonMaster.browse(int(data['requested_central_prison']))
            if not central.exists() or central.prison_type != 'central':
                return self._err('Invalid requested_central_prison id')

            district = PrisonMaster.browse(int(data['requested_district_jail']))
            if not district.exists() or district.prison_type != 'district':
                return self._err('Invalid requested_district_jail id')

            sub = PrisonMaster.browse(int(data['requested_sub_jail']))
            if not sub.exists() or sub.prison_type != 'sub':
                return self._err('Invalid requested_sub_jail id')

            # --- Prevent duplicate pending requests for the same employee ---
            existing = env['transfer.approval.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending'),
                ('active', '=', True),
            ], limit=1)
            if existing:
                return self._err(
                    f'Employee already has a pending transfer request (id={existing.id})'
                )

            # --- Auto-populate current prison details -----------------------
            TransferRequest = env['transfer.approval.request']
            current_vals = TransferRequest._current_prison_vals_from_employee(employee)

            # --- Create record ----------------------------------------------
            new_request = TransferRequest.sudo().with_context(
                mail_notrack=True
            ).create({
                'employee_id': employee.id,
                'requested_central_prison': central.id,
                'requested_district_jail': district.id,
                'requested_sub_jail': sub.id,
                'approval_user_id': approval_user.id,
                'requested_by': env.user.id,
                'state': 'pending',
                'remarks': data.get('remarks', ''),
                **current_vals,
            })

            _logger.info(
                'Transfer approval request %d created for employee %d by user %d',
                new_request.id, employee.id, env.user.id,
            )

            return self._ok(
                'Transfer approval request created successfully',
                request_id=new_request.id,
            )

        except Exception as exc:
            _logger.exception('POST /api/transfer/save-approval-request failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ------------------------------------------------------------------
    # API 2 – Fetch Approval Requests (for logged-in approval user)
    # GET /api/transfer/fetch-approval-requests
    # ------------------------------------------------------------------

    @http.route(
        '/api/transfer/fetch-approval-requests',
        auth='user',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def fetch_approval_requests(self, **kwargs):
        """
        List pending transfer approval requests assigned to the logged-in user.

        Query params
        ------------
        page   int  (default 1)
        limit  int  (default 20, max 100)
        """
        try:
            # --- Pagination -------------------------------------------------
            try:
                page = max(1, int(kwargs.get('page', 1)))
                limit = max(1, min(_MAX_LIMIT, int(kwargs.get('limit', 20))))
            except (TypeError, ValueError) as exc:
                return self._err(f'Invalid pagination parameter: {exc}')

            offset = (page - 1) * limit
            uid = request.env.user.id

            domain = [
                ('approval_user_id', '=', uid),
                ('state', '=', 'pending'),
                ('active', '=', True),
            ]

            TransferRequest = request.env['transfer.approval.request'].sudo()
            total_count = TransferRequest.search_count(domain)
            records = TransferRequest.search(domain, offset=offset, limit=limit)

            return self._json_response({
                'success': True,
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'data': [self._format_request(r) for r in records],
            })

        except Exception as exc:
            _logger.exception('GET /api/transfer/fetch-approval-requests failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ------------------------------------------------------------------
    # API 3 – Accept (Approve) Approval Request
    # POST /api/transfer/accept-approval-request
    # ------------------------------------------------------------------

    @http.route(
        '/api/transfer/accept-approval-request',
        auth='user',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def accept_approval_request(self, **_kwargs):
        """
        Approve a pending transfer request and update the employee's prison details.

        Body (JSON)
        -----------
        request_id  int  required
        """
        try:
            data, err = self._parse_json_body()
            if err:
                return err

            if not data.get('request_id'):
                return self._err('Missing required field: request_id')

            uid = request.env.user.id
            env = request.env

            tar = env['transfer.approval.request'].sudo().browse(
                int(data['request_id'])
            )
            if not tar.exists():
                return self._err('Transfer request not found', status=404)

            # Only the assigned approval user may approve
            if tar.approval_user_id.id != uid:
                return self._err(
                    'You are not authorised to approve this request', status=403
                )

            if tar.state != 'pending':
                return self._err(
                    f'Request is already {tar.state} and cannot be approved'
                )

            # --- Update employee prison details (transactional) -------------
            tar.employee_id.sudo().write({
                'x_central_prison': tar.requested_central_prison.name,
                'x_district_jail': tar.requested_district_jail.name,
                'x_sub_jail': tar.requested_sub_jail.name,
            })

            # --- Mark request as approved -----------------------------------
            tar.sudo().write({
                'state': 'approved',
                'approved_by': uid,
                'approved_date': fields.Datetime.now(),
            })

            _logger.info(
                'Transfer request %d approved by user %d; employee %d moved to %s / %s / %s',
                tar.id, uid, tar.employee_id.id,
                tar.requested_central_prison.name,
                tar.requested_district_jail.name,
                tar.requested_sub_jail.name,
            )

            return self._ok('Transfer approved successfully')

        except Exception as exc:
            _logger.exception('POST /api/transfer/accept-approval-request failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ------------------------------------------------------------------
    # API 4 – Reject Approval Request
    # POST /api/transfer/reject-approval-request
    # ------------------------------------------------------------------

    @http.route(
        '/api/transfer/reject-approval-request',
        auth='user',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def reject_approval_request(self, **_kwargs):
        """
        Reject a pending transfer request.

        Body (JSON)
        -----------
        request_id  int  required
        remarks     str  optional (rejection reason)
        """
        try:
            data, err = self._parse_json_body()
            if err:
                return err

            if not data.get('request_id'):
                return self._err('Missing required field: request_id')

            uid = request.env.user.id
            env = request.env

            tar = env['transfer.approval.request'].sudo().browse(
                int(data['request_id'])
            )
            if not tar.exists():
                return self._err('Transfer request not found', status=404)

            # Only the assigned approval user may reject
            if tar.approval_user_id.id != uid:
                return self._err(
                    'You are not authorised to reject this request', status=403
                )

            if tar.state != 'pending':
                return self._err(
                    f'Request is already {tar.state} and cannot be rejected'
                )

            update_vals = {
                'state': 'rejected',
                'approved_by': uid,
                'approved_date': fields.Datetime.now(),
            }
            if data.get('remarks'):
                update_vals['remarks'] = data['remarks']

            tar.sudo().write(update_vals)

            _logger.info(
                'Transfer request %d rejected by user %d', tar.id, uid
            )

            return self._ok('Transfer request rejected successfully')

        except Exception as exc:
            _logger.exception('POST /api/transfer/reject-approval-request failed: %s', exc)
            return self._err('Internal server error', status=500)
