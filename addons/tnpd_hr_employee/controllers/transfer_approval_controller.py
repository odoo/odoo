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

    # ==================================================================
    # RESPONSE HELPERS
    # ==================================================================

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
        return self._json_response(
            {'success': False, 'message': message}, status=status
        )

    # ==================================================================
    # AUTH HELPER
    # Why auth='none' instead of auth='user'?
    # ------------------------------------------------------------------
    # When the Odoo website module is installed, auth='user' routes that
    # receive an unauthenticated (or expired-session) request are
    # intercepted by the website controller and served as an HTML login
    # page instead of a JSON response. For REST APIs that must always
    # return JSON, we declare auth='none' and validate the session
    # manually via request.session.uid.
    # ==================================================================

    def _require_auth(self):
        """
        Validate that the caller has an active Odoo session.

        Returns (uid, None) on success or (None, error_response) on failure.
        """
        uid = request.session.uid
        if not uid:
            return None, self._err(
                'Authentication required. '
                'POST to /web/session/authenticate first.',
                status=401,
            )
        return uid, None

    def _parse_json_body(self):
        """
        Parse the request body as JSON.
        Returns (data_dict, None) on success, or (None, error_response) on failure.
        """
        try:
            data = json.loads(request.httprequest.data or '{}')
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object at the top level.')
            return data, None
        except (json.JSONDecodeError, ValueError) as exc:
            return None, self._err(f'Invalid JSON body: {exc}')

    # ==================================================================
    # SERIALIZER
    # ==================================================================

    def _format_jail(self, jail_record):
        """Serialize a prison.jail Many2one value."""
        if not jail_record:
            return {'id': None, 'name': ''}
        return {'id': jail_record.id, 'name': jail_record.name}

    def _format_request(self, rec):
        """Serialize a transfer.approval.request record for API responses."""
        return {
            'request_id':               rec.id,
            'employee_id':              rec.employee_id.id,
            'employee_name':            rec.employee_id.name or '',
            # Current posting snapshot
            'current_central_prison':   self._format_jail(rec.current_central_prison),
            'current_district_jail':    self._format_jail(rec.current_district_jail),
            'current_sub_jail':         self._format_jail(rec.current_sub_jail),
            # Requested destination
            'requested_central_prison': self._format_jail(rec.requested_central_prison),
            'requested_district_jail':  self._format_jail(rec.requested_district_jail),
            'requested_sub_jail':       self._format_jail(rec.requested_sub_jail),
            # Workflow
            'state':          rec.state,
            'requested_by':   rec.requested_by.name or '',
            'approval_user':  {'id': rec.approval_user_id.id, 'name': rec.approval_user_id.name or ''},
            'approved_by':    rec.approved_by.name or '',
            'approved_date':  str(rec.approved_date) if rec.approved_date else '',
            'remarks':        rec.remarks or '',
            'create_date':    str(rec.create_date) if rec.create_date else '',
        }

    # ==================================================================
    # API 0 – Prison / Jail Master Lookup
    # GET /api/transfer/prison-master
    #
    # Legacy endpoint — returns all jails grouped by type.
    # New clients should use the prison_jail_master module's dedicated
    # endpoints: /api/jails/central, /api/jails/district, /api/jails/sub
    # ==================================================================

    @http.route(
        '/api/transfer/prison-master',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_prison_master(self, **_kwargs):
        """
        Return all active jail records grouped by type.

        No authentication required — used by clients to seed dropdowns.

        Response
        --------
        {
            "success": true,
            "data": {
                "central_jails":  [{"id": 1, "name": "...", "code": "..."}, ...],
                "district_jails": [...],
                "sub_jails":      [...]
            }
        }
        """
        try:
            Jail = request.env['prison.jail'].sudo()

            def _fetch(jail_type):
                records = Jail.search(
                    [('jail_type', '=', jail_type), ('active', '=', True)],
                    order='sequence, name asc',
                )
                return [
                    {'id': r.id, 'name': r.name, 'code': r.code or '',
                     'parent_id': r.parent_id.id if r.parent_id else None}
                    for r in records
                ]

            return self._json_response({
                'success': True,
                'data': {
                    'central_jails':  _fetch('central_jail'),
                    'district_jails': _fetch('district_jail'),
                    'sub_jails':      _fetch('sub_jail'),
                },
            })

        except Exception as exc:
            _logger.exception('GET /api/transfer/prison-master failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 1 – Create Transfer Approval Request
    # POST /api/transfer/save-approval-request
    # ==================================================================

    @http.route(
        '/api/transfer/save-approval-request',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def save_approval_request(self, **_kwargs):
        """
        Create a new transfer approval request.

        Body (JSON)
        -----------
        employee_id               int  required
        requested_central_prison  int  required  (prison.jail id, jail_type=central_jail)
        requested_district_jail   int  required  (prison.jail id, jail_type=district_jail)
        requested_sub_jail        int  required  (prison.jail id, jail_type=sub_jail)
        approval_user_id          int  required
        remarks                   str  optional

        Hierarchy validation
        --------------------
        • district jail must be a child of the given central jail
        • sub jail must be a child of the given district jail
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            data, err = self._parse_json_body()
            if err:
                return err

            # --- Required field presence -----------------------------------
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

            env = request.env(user=uid)

            # --- Validate employee -----------------------------------------
            employee = env['hr.employee'].sudo().browse(int(data['employee_id']))
            if not employee.exists():
                return self._err('Employee not found', status=404)

            # --- Validate approval user ------------------------------------
            approval_user = env['res.users'].sudo().browse(int(data['approval_user_id']))
            if not approval_user.exists():
                return self._err('Approval user not found', status=404)

            # --- Validate jail records and hierarchy -----------------------
            Jail = env['prison.jail'].sudo()

            central = Jail.browse(int(data['requested_central_prison']))
            if not central.exists() or central.jail_type != 'central_jail':
                return self._err(
                    'Invalid requested_central_prison: must be a prison.jail record '
                    'with jail_type=central_jail'
                )

            district = Jail.browse(int(data['requested_district_jail']))
            if not district.exists() or district.jail_type != 'district_jail':
                return self._err(
                    'Invalid requested_district_jail: must be a prison.jail record '
                    'with jail_type=district_jail'
                )
            if district.parent_id != central:
                return self._err(
                    f'District Jail "{district.name}" does not belong to '
                    f'Central Jail "{central.name}".'
                )

            sub = Jail.browse(int(data['requested_sub_jail']))
            if not sub.exists() or sub.jail_type != 'sub_jail':
                return self._err(
                    'Invalid requested_sub_jail: must be a prison.jail record '
                    'with jail_type=sub_jail'
                )
            if sub.parent_id != district:
                return self._err(
                    f'Sub Jail "{sub.name}" does not belong to '
                    f'District Jail "{district.name}".'
                )

            # --- Prevent duplicate pending requests -----------------------
            existing = env['transfer.approval.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending'),
                ('active', '=', True),
            ], limit=1)
            if existing:
                return self._err(
                    f'Employee already has a pending transfer request '
                    f'(id={existing.id})'
                )

            # --- Auto-populate current posting snapshot -------------------
            TransferRequest = env['transfer.approval.request']
            current_vals = TransferRequest._current_prison_vals_from_employee(employee)

            # --- Create record ---------------------------------------------
            new_request = TransferRequest.sudo().with_context(
                mail_notrack=True
            ).create({
                'employee_id':             employee.id,
                'requested_central_prison': central.id,
                'requested_district_jail': district.id,
                'requested_sub_jail':      sub.id,
                'approval_user_id':        approval_user.id,
                'requested_by':            uid,
                'state':                   'pending',
                'remarks':                 data.get('remarks', ''),
                **current_vals,
            })

            _logger.info(
                'Transfer request %d created — employee=%d by user=%d',
                new_request.id, employee.id, uid,
            )

            return self._ok(
                'Transfer approval request created successfully',
                request_id=new_request.id,
            )

        except Exception as exc:
            _logger.exception(
                'POST /api/transfer/save-approval-request failed: %s', exc
            )
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 2 – Fetch Pending Approval Requests
    # GET /api/transfer/fetch-approval-requests
    # ==================================================================

    @http.route(
        '/api/transfer/fetch-approval-requests',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def fetch_approval_requests(self, **kwargs):
        """
        List pending transfer requests assigned to the logged-in approval user.

        Query params
        ------------
        page   int  (default 1)
        limit  int  (default 20, max 100)
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            try:
                page  = max(1, int(kwargs.get('page', 1)))
                limit = max(1, min(_MAX_LIMIT, int(kwargs.get('limit', 20))))
            except (TypeError, ValueError) as exc:
                return self._err(f'Invalid pagination parameter: {exc}')

            offset = (page - 1) * limit
            env    = request.env(user=uid)

            domain = [
                ('approval_user_id', '=', uid),
                ('state',            '=', 'pending'),
                ('active',           '=', True),
            ]

            TransferRequest = env['transfer.approval.request'].sudo()
            total_count     = TransferRequest.search_count(domain)
            records         = TransferRequest.search(
                domain, offset=offset, limit=limit
            )

            return self._json_response({
                'success':     True,
                'page':        page,
                'limit':       limit,
                'total_count': total_count,
                'data':        [self._format_request(r) for r in records],
            })

        except Exception as exc:
            _logger.exception(
                'GET /api/transfer/fetch-approval-requests failed: %s', exc
            )
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 3 – Accept (Approve) Transfer Request
    # POST /api/transfer/accept-approval-request
    # ==================================================================

    @http.route(
        '/api/transfer/accept-approval-request',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def accept_approval_request(self, **_kwargs):
        """
        Approve a pending transfer request and update the employee's jail posting.

        On approval:
        • Employee's x_central_jail_id / x_district_jail_id / x_sub_jail_id
          (Many2one) fields are updated to the requested jail records.
        • Legacy Char fields (x_central_prison / x_district_jail / x_sub_jail)
          are also synced for backward compatibility.
        • x_date_present_station is set to today.
        • A dated entry is prepended to x_service_history.

        Body (JSON)
        -----------
        request_id  int  required
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            data, err = self._parse_json_body()
            if err:
                return err

            if not data.get('request_id'):
                return self._err('Missing required field: request_id')

            env = request.env(user=uid)

            tar = env['transfer.approval.request'].sudo().browse(
                int(data['request_id'])
            )
            if not tar.exists():
                return self._err('Transfer request not found', status=404)

            if tar.approval_user_id.id != uid:
                return self._err(
                    'You are not authorised to approve this request',
                    status=403,
                )

            if tar.state != 'pending':
                return self._err(
                    f'Request is already {tar.state} and cannot be approved'
                )

            # --- Snapshot old posting before overwriting ------------------
            emp = tar.employee_id.sudo()
            old_central  = emp.x_central_jail_id.name  or emp.x_central_prison  or '-'
            old_district = emp.x_district_jail_id.name or emp.x_district_jail   or '-'
            old_sub      = emp.x_sub_jail_id.name      or emp.x_sub_jail         or '-'

            new_central  = tar.requested_central_prison.name
            new_district = tar.requested_district_jail.name
            new_sub      = tar.requested_sub_jail.name

            approved_date_now = fields.Datetime.now()
            approved_date_str = approved_date_now.strftime('%d-%b-%Y')

            # --- Build service history entry ------------------------------
            history_line = (
                f"[{approved_date_str}] Transfer Approved | "
                f"From: {old_central} / {old_district} / {old_sub} "
                f"→ To: {new_central} / {new_district} / {new_sub} | "
                f"Approved By: {tar.approval_user_id.name} | "
                f"Ref: TRF/{tar.id}"
            )
            existing_history = emp.x_service_history or ''
            updated_history = (
                history_line + '\n' + existing_history
                if existing_history.strip()
                else history_line
            )

            # --- Update employee — Many2one jail fields + legacy Char sync ---
            emp.write({
                # New hierarchy-aware Many2one fields (primary)
                'x_central_jail_id':      tar.requested_central_prison.id,
                'x_district_jail_id':     tar.requested_district_jail.id,
                'x_sub_jail_id':          tar.requested_sub_jail.id,
                # Legacy Char fields kept in sync for backward compatibility
                'x_central_prison':       new_central,
                'x_district_jail':        new_district,
                'x_sub_jail':             new_sub,
                'x_date_present_station': approved_date_now.date(),
                'x_service_history':      updated_history,
            })

            # --- Mark request as approved ---------------------------------
            tar.sudo().write({
                'state':         'approved',
                'approved_by':   uid,
                'approved_date': approved_date_now,
            })

            _logger.info(
                'Transfer request %d approved by user=%d; '
                'employee=%d → central=%s district=%s sub=%s',
                tar.id, uid, emp.id,
                new_central, new_district, new_sub,
            )

            return self._ok('Transfer approved successfully')

        except Exception as exc:
            _logger.exception(
                'POST /api/transfer/accept-approval-request failed: %s', exc
            )
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 4 – Reject Transfer Request
    # POST /api/transfer/reject-approval-request
    # ==================================================================

    @http.route(
        '/api/transfer/reject-approval-request',
        auth='none',
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
        remarks     str  optional  (rejection reason)
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            data, err = self._parse_json_body()
            if err:
                return err

            if not data.get('request_id'):
                return self._err('Missing required field: request_id')

            env = request.env(user=uid)

            tar = env['transfer.approval.request'].sudo().browse(
                int(data['request_id'])
            )
            if not tar.exists():
                return self._err('Transfer request not found', status=404)

            if tar.approval_user_id.id != uid:
                return self._err(
                    'You are not authorised to reject this request',
                    status=403,
                )

            if tar.state != 'pending':
                return self._err(
                    f'Request is already {tar.state} and cannot be rejected'
                )

            update_vals = {
                'state':         'rejected',
                'approved_by':   uid,
                'approved_date': fields.Datetime.now(),
            }
            if data.get('remarks'):
                update_vals['remarks'] = data['remarks']

            tar.sudo().write(update_vals)

            _logger.info(
                'Transfer request %d rejected by user=%d', tar.id, uid
            )

            return self._ok('Transfer request rejected successfully')

        except Exception as exc:
            _logger.exception(
                'POST /api/transfer/reject-approval-request failed: %s', exc
            )
            return self._err('Internal server error', status=500)
