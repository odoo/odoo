# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

import json
import logging
from datetime import date

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Hard cap on records returned per page.
_MAX_LIMIT = 100

# Tenure threshold in days (3 years).
_TENURE_DAYS = 1095


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
        # Compute tenure_years if employee has x_date_present_station
        tenure_years = None
        try:
            emp = rec.employee_id
            if emp and emp.x_date_present_station:
                delta = date.today() - emp.x_date_present_station
                tenure_years = round(delta.days / 365.25, 1)
        except Exception:
            pass

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
            # Extended fields
            'transfer_type':   getattr(rec, 'transfer_type', '') or '',
            'transfer_reason': getattr(rec, 'transfer_reason', '') or '',
            'priority':        getattr(rec, 'priority', '') or '',
            'tenure_years':    tenure_years,
        }

    # ==================================================================
    # INTERNAL: Update employee jail posting (shared by approve + admin)
    # ==================================================================

    def _apply_transfer_to_employee(self, emp, tar, approved_by_user, approved_date_now, note_prefix='Transfer Approved'):
        """Write jail posting fields to the employee record and append service history."""
        old_central  = emp.x_central_jail_id.name  or emp.x_central_prison  or '-'
        old_district = emp.x_district_jail_id.name or emp.x_district_jail   or '-'
        old_sub      = emp.x_sub_jail_id.name      or emp.x_sub_jail         or '-'

        new_central  = tar.requested_central_prison.name
        new_district = tar.requested_district_jail.name
        new_sub      = tar.requested_sub_jail.name

        approved_date_str = approved_date_now.strftime('%d-%b-%Y')

        history_line = (
            f"[{approved_date_str}] {note_prefix} | "
            f"From: {old_central} / {old_district} / {old_sub} "
            f"→ To: {new_central} / {new_district} / {new_sub} | "
            f"By: {approved_by_user.name} | "
            f"Ref: TRF/{tar.id}"
        )
        existing_history = emp.x_service_history or ''
        updated_history = (
            history_line + '\n' + existing_history
            if existing_history.strip()
            else history_line
        )

        emp.write({
            'x_central_jail_id':      tar.requested_central_prison.id,
            'x_district_jail_id':     tar.requested_district_jail.id,
            'x_sub_jail_id':          tar.requested_sub_jail.id,
            'x_central_prison':       new_central,
            'x_district_jail':        new_district,
            'x_sub_jail':             new_sub,
            'x_date_present_station': approved_date_now.date(),
            'x_service_history':      updated_history,
        })

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

            central_data  = _fetch('central_jail')
            district_data = _fetch('district_jail')
            sub_data      = _fetch('sub_jail')

            return self._json_response({
                'success':       True,
                'central_jails':  central_data,
                'district_jails': district_data,
                'sub_jails':      sub_data,
                'data': {
                    'central_jails':  central_data,
                    'district_jails': district_data,
                    'sub_jails':      sub_data,
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
                'total':       total_count,
                'total_count': total_count,
                'records':     [self._format_request(r) for r in records],
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

            emp = tar.employee_id.sudo()
            approved_date_now = fields.Datetime.now()

            self._apply_transfer_to_employee(
                emp, tar,
                approved_by_user=env['res.users'].sudo().browse(uid),
                approved_date_now=approved_date_now,
                note_prefix='Transfer Approved',
            )

            tar.sudo().write({
                'state':         'approved',
                'approved_by':   uid,
                'approved_date': approved_date_now,
            })

            _logger.info(
                'Transfer request %d approved by user=%d; employee=%d',
                tar.id, uid, emp.id,
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

    # ==================================================================
    # API 5 – List All Transfer Requests
    # GET /api/transfer/list-all
    # ==================================================================

    @http.route(
        '/api/transfer/list-all',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def list_all_requests(self, **kwargs):
        """
        List all transfer requests with optional filters.

        Query params
        ------------
        page          int  (default 1)
        limit         int  (default 20, max 100)
        state         str  optional — filter by workflow state
        transfer_type str  optional — filter by transfer_type field
        search        str  optional — partial match on employee name
        employee_id   int  optional — filter by specific employee
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

            domain = [('active', '=', True)]

            if kwargs.get('state'):
                domain.append(('state', '=', kwargs['state']))

            if kwargs.get('transfer_type'):
                domain.append(('transfer_type', '=', kwargs['transfer_type']))

            if kwargs.get('employee_id'):
                try:
                    domain.append(('employee_id', '=', int(kwargs['employee_id'])))
                except (TypeError, ValueError):
                    return self._err('employee_id must be an integer')

            if kwargs.get('search'):
                domain.append(('employee_id.name', 'ilike', kwargs['search']))

            TransferRequest = env['transfer.approval.request'].sudo()
            total_count     = TransferRequest.search_count(domain)
            records         = TransferRequest.search(
                domain, offset=offset, limit=limit, order='id desc'
            )

            return self._json_response({
                'success':     True,
                'page':        page,
                'limit':       limit,
                'total':       total_count,
                'total_count': total_count,
                'records':     [self._format_request(r) for r in records],
                'data':        [self._format_request(r) for r in records],
            })

        except Exception as exc:
            _logger.exception('GET /api/transfer/list-all failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 6 – Create Draft Transfer Request
    # POST /api/transfer/create-draft
    # ==================================================================

    @http.route(
        '/api/transfer/create-draft',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def create_draft_request(self, **_kwargs):
        """
        Create a new DRAFT transfer request (transfer_type='request').

        Body (JSON)
        -----------
        employee_id               int  required
        requested_central_prison  int  required
        requested_district_jail   int  optional
        requested_sub_jail        int  required
        transfer_reason           str  optional
        priority                  str  optional (default='medium')
        approval_user_id          int  required
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            data, err = self._parse_json_body()
            if err:
                return err

            required = ['employee_id', 'requested_central_prison', 'requested_sub_jail']
            missing  = [f for f in required if not data.get(f)]
            if missing:
                return self._err(f'Missing required fields: {", ".join(missing)}')

            env = request.env(user=uid)

            # --- Validate employee ---
            employee = env['hr.employee'].sudo().browse(int(data['employee_id']))
            if not employee.exists():
                return self._err('Employee not found', status=404)

            # --- Validate approval user (defaults to requesting user) ---
            approval_user_id_raw = data.get('approval_user_id') or uid
            approval_user = env['res.users'].sudo().browse(int(approval_user_id_raw))
            if not approval_user.exists():
                return self._err('Approval user not found', status=404)

            # --- Validate jails ---
            Jail = env['prison.jail'].sudo()

            central = Jail.browse(int(data['requested_central_prison']))
            if not central.exists() or central.jail_type != 'central_jail':
                return self._err('Invalid requested_central_prison')

            district_id = None
            if data.get('requested_district_jail'):
                district = Jail.browse(int(data['requested_district_jail']))
                if not district.exists() or district.jail_type != 'district_jail':
                    return self._err('Invalid requested_district_jail')
                if district.parent_id != central:
                    return self._err(
                        f'District Jail "{district.name}" does not belong to Central Jail "{central.name}".'
                    )
                district_id = district.id

            sub = Jail.browse(int(data['requested_sub_jail']))
            if not sub.exists() or sub.jail_type != 'sub_jail':
                return self._err('Invalid requested_sub_jail')

            # --- Check no existing draft/pending request ---
            existing = env['transfer.approval.request'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['draft', 'pending']),
                ('active', '=', True),
            ], limit=1)
            if existing:
                return self._err(
                    f'Employee already has an open transfer request (id={existing.id}, state={existing.state})'
                )

            TransferRequest = env['transfer.approval.request']
            current_vals = TransferRequest._current_prison_vals_from_employee(employee)

            create_vals = {
                'employee_id':             employee.id,
                'requested_central_prison': central.id,
                'requested_sub_jail':      sub.id,
                'approval_user_id':        approval_user.id,
                'requested_by':            uid,
                'state':                   'draft',
                'transfer_type':           'request',
                'transfer_reason':         data.get('transfer_reason', ''),
                'priority':                data.get('priority', 'medium'),
                **current_vals,
            }
            if district_id:
                create_vals['requested_district_jail'] = district_id

            new_request = TransferRequest.sudo().with_context(mail_notrack=True).create(create_vals)

            _logger.info(
                'Draft transfer request %d created — employee=%d by user=%d',
                new_request.id, employee.id, uid,
            )

            return self._ok('Draft transfer request created successfully', request_id=new_request.id)

        except Exception as exc:
            _logger.exception('POST /api/transfer/create-draft failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 7 – Submit Draft Request to Pending
    # POST /api/transfer/submit-request
    # ==================================================================

    @http.route(
        '/api/transfer/submit-request',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def submit_request(self, **_kwargs):
        """
        Submit a draft transfer request to pending state.

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

            tar = env['transfer.approval.request'].sudo().browse(int(data['request_id']))
            if not tar.exists():
                return self._err('Transfer request not found', status=404)

            if tar.state != 'draft':
                return self._err(
                    f'Request is in state "{tar.state}"; only draft requests can be submitted'
                )

            # Allow requester or approval user
            current_user = env['res.users'].sudo().browse(uid)
            is_requester = tar.requested_by.id == uid
            is_approver  = tar.approval_user_id.id == uid
            if not (is_requester or is_approver):
                return self._err('You are not authorised to submit this request', status=403)

            # Call action_submit if available, else set state directly
            if hasattr(tar, 'action_submit'):
                tar.action_submit()
            else:
                tar.sudo().write({'state': 'pending'})

            _logger.info('Transfer request %d submitted by user=%d', tar.id, uid)

            return self._ok('Transfer request submitted successfully')

        except Exception as exc:
            _logger.exception('POST /api/transfer/submit-request failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 8 – Cancel Transfer Request
    # POST /api/transfer/cancel-request
    # ==================================================================

    @http.route(
        '/api/transfer/cancel-request',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def cancel_request(self, **_kwargs):
        """
        Cancel a draft or pending transfer request.

        Body (JSON)
        -----------
        request_id  int  required
        remarks     str  optional
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

            tar = env['transfer.approval.request'].sudo().browse(int(data['request_id']))
            if not tar.exists():
                return self._err('Transfer request not found', status=404)

            if tar.state not in ('draft', 'pending'):
                return self._err(
                    f'Request is in state "{tar.state}"; only draft or pending requests can be cancelled'
                )

            update_vals = {'state': 'cancelled'}
            if data.get('remarks'):
                update_vals['remarks'] = data['remarks']

            tar.sudo().write(update_vals)

            _logger.info('Transfer request %d cancelled by user=%d', tar.id, uid)

            return self._ok('Transfer request cancelled successfully')

        except Exception as exc:
            _logger.exception('POST /api/transfer/cancel-request failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 9 – Eligible Tenure Transfer Employees
    # GET /api/transfer/eligible-tenure
    # ==================================================================

    @http.route(
        '/api/transfer/eligible-tenure',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def eligible_tenure(self, **kwargs):
        """
        Return employees eligible for tenure transfer (>= 3 years at current station).

        Query params
        ------------
        page    int  (default 1)
        limit   int  (default 20, max 100)
        search  str  optional — partial match on employee name
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

            return self._json_response(
                self._get_eligible_employees(
                    uid=uid,
                    page=page,
                    limit=limit,
                    search=kwargs.get('search', ''),
                    exclude_applied=False,
                )
            )

        except Exception as exc:
            _logger.exception('GET /api/transfer/eligible-tenure failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 10 – Eligible Admin (Tenure) Transfer Employees
    # GET /api/transfer/eligible-admin
    # ==================================================================

    @http.route(
        '/api/transfer/eligible-admin',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def eligible_admin(self, **kwargs):
        """
        Like eligible-tenure but also excludes employees who have applied
        for tenure transfer in any state.

        Query params
        ------------
        page    int  (default 1)
        limit   int  (default 20, max 100)
        search  str  optional
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

            return self._json_response(
                self._get_eligible_employees(
                    uid=uid,
                    page=page,
                    limit=limit,
                    search=kwargs.get('search', ''),
                    exclude_applied=True,
                )
            )

        except Exception as exc:
            _logger.exception('GET /api/transfer/eligible-admin failed: %s', exc)
            return self._err('Internal server error', status=500)

    def _get_eligible_employees(self, uid, page, limit, search, exclude_applied):
        """
        Shared logic for eligible-tenure and eligible-admin endpoints.

        exclude_applied=False: exclude only employees with draft/pending tenure transfer.
        exclude_applied=True:  exclude employees with any tenure transfer (any state).
        """
        env = request.env(user=uid)
        today = date.today()

        # Find employees with tenure >= 3 years
        emp_domain = [('x_date_present_station', '!=', False)]
        if search:
            emp_domain.append(('name', 'ilike', search))

        all_employees = env['hr.employee'].sudo().search(emp_domain)

        # Filter by tenure threshold
        eligible = []
        for emp in all_employees:
            if not emp.x_date_present_station:
                continue
            delta = today - emp.x_date_present_station
            if delta.days < _TENURE_DAYS:
                continue
            eligible.append((emp, delta.days))

        # Find employees with existing tenure transfers to exclude
        if exclude_applied:
            tenure_blocked_domain = [
                ('transfer_type', '=', 'tenure'),
                ('active', '=', True),
            ]
        else:
            tenure_blocked_domain = [
                ('transfer_type', '=', 'tenure'),
                ('state', 'in', ['draft', 'pending']),
                ('active', '=', True),
            ]

        blocked_requests = env['transfer.approval.request'].sudo().search(tenure_blocked_domain)
        blocked_emp_ids  = set(blocked_requests.mapped('employee_id').ids)

        # Filter out blocked employees
        eligible = [(emp, days) for emp, days in eligible if emp.id not in blocked_emp_ids]

        # Determine if any other prison has vacancy
        has_any_vacancy = False
        try:
            Vacancy = env['prison.vacancy'].sudo()
            has_any_vacancy = bool(Vacancy.search([('vacancy_count', '>', 0)], limit=1))
        except Exception:
            pass  # prison.vacancy may not be installed

        # Paginate
        total_count = len(eligible)
        offset = (page - 1) * limit
        page_slice = eligible[offset: offset + limit]

        data = []
        for emp, days in page_slice:
            tenure_years = round(days / 365.25, 1)

            # Check vacancy at OTHER prisons (not current sub jail)
            emp_vacancy = has_any_vacancy  # simplified: any vacancy anywhere
            try:
                if emp.x_sub_jail_id:
                    vacancy_elsewhere = env['prison.vacancy'].sudo().search([
                        ('vacancy_count', '>', 0),
                        ('prison_id', '!=', emp.x_sub_jail_id.id),
                    ], limit=1)
                    emp_vacancy = bool(vacancy_elsewhere)
            except Exception:
                pass

            data.append({
                'employee_id':      emp.id,
                'employee_name':    emp.name or '',
                'employee_code':    emp.x_employee_code or '',
                'designation':      emp.x_designation or '',
                'rank':             emp.job_id.name if emp.job_id else '',
                'current_central_prison': self._format_jail(emp.x_central_jail_id),
                'current_district_jail':  self._format_jail(emp.x_district_jail_id),
                'current_sub_jail':       self._format_jail(emp.x_sub_jail_id),
                'date_present_station':   str(emp.x_date_present_station),
                'tenure_years':           tenure_years,
                'is_eligible':            True,
                'has_vacancy_elsewhere':  emp_vacancy,
            })

        return {
            'success':     True,
            'page':        page,
            'limit':       limit,
            'total_count': total_count,
            'total':       total_count,
            'employees':   data,
            'data':        data,
        }

    # ==================================================================
    # API 11 – Admin-Initiated Transfer
    # POST /api/transfer/admin-initiate-transfer
    # ==================================================================

    @http.route(
        '/api/transfer/admin-initiate-transfer',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def admin_initiate_transfer(self, **_kwargs):
        """
        Super admin creates an administrative grounds transfer directly.
        The request is created in 'approved' state and the employee's posting
        is updated immediately — no approval workflow required.

        Body (JSON)
        -----------
        employee_id               int  required
        requested_central_prison  int  required
        requested_district_jail   int  optional
        requested_sub_jail        int  required
        remarks                   str  optional
        priority                  str  optional (default='high')
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            data, err = self._parse_json_body()
            if err:
                return err

            required = ['employee_id', 'requested_central_prison', 'requested_sub_jail']
            missing  = [f for f in required if not data.get(f)]
            if missing:
                return self._err(f'Missing required fields: {", ".join(missing)}')

            env = request.env(user=uid)

            employee = env['hr.employee'].sudo().browse(int(data['employee_id']))
            if not employee.exists():
                return self._err('Employee not found', status=404)

            Jail = env['prison.jail'].sudo()

            central = Jail.browse(int(data['requested_central_prison']))
            if not central.exists() or central.jail_type != 'central_jail':
                return self._err('Invalid requested_central_prison')

            district_id = None
            if data.get('requested_district_jail'):
                district = Jail.browse(int(data['requested_district_jail']))
                if not district.exists() or district.jail_type != 'district_jail':
                    return self._err('Invalid requested_district_jail')
                district_id = district.id

            sub = Jail.browse(int(data['requested_sub_jail']))
            if not sub.exists() or sub.jail_type != 'sub_jail':
                return self._err('Invalid requested_sub_jail')

            approved_date_now = fields.Datetime.now()
            current_user      = env['res.users'].sudo().browse(uid)

            TransferRequest = env['transfer.approval.request']
            current_vals = TransferRequest._current_prison_vals_from_employee(employee)

            create_vals = {
                'employee_id':              employee.id,
                'requested_central_prison': central.id,
                'requested_sub_jail':       sub.id,
                'approval_user_id':         uid,
                'requested_by':             uid,
                'approved_by':              uid,
                'approved_date':            approved_date_now,
                'state':                    'approved',
                'transfer_type':            'admin_grounds',
                'priority':                 data.get('priority', 'high'),
                'remarks':                  data.get('remarks', ''),
                **current_vals,
            }
            if district_id:
                create_vals['requested_district_jail'] = district_id

            new_request = TransferRequest.sudo().with_context(mail_notrack=True).create(create_vals)

            # Update employee posting immediately
            self._apply_transfer_to_employee(
                emp=employee.sudo(),
                tar=new_request,
                approved_by_user=current_user,
                approved_date_now=approved_date_now,
                note_prefix='Admin Transfer',
            )

            _logger.info(
                'Admin transfer %d created and applied — employee=%d by user=%d',
                new_request.id, employee.id, uid,
            )

            return self._ok(
                'Administrative transfer completed successfully',
                request_id=new_request.id,
            )

        except Exception as exc:
            _logger.exception('POST /api/transfer/admin-initiate-transfer failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 12 – Vacancy Summary
    # GET /api/transfer/vacancy-summary
    # ==================================================================

    @http.route(
        '/api/transfer/vacancy-summary',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def vacancy_summary(self, **_kwargs):
        """
        Return vacancy data for all prisons.

        Response
        --------
        {
            "success": true,
            "data": [
                {
                    "prison_id": 1,
                    "prison_name": "...",
                    "prison_type": "...",
                    "sanctioned_strength": 50,
                    "occupied_count": 40,
                    "vacancy_count": 10
                },
                ...
            ]
        }
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            env = request.env(user=uid)

            try:
                vacancies = env['prison.vacancy'].sudo().search([])
            except Exception as exc:
                _logger.warning('prison.vacancy model not found: %s', exc)
                return self._json_response({
                    'success': True,
                    'data': [],
                    'note': 'prison.vacancy model is not installed',
                })

            data = []
            for v in vacancies:
                prison = getattr(v, 'prison_id', None)
                data.append({
                    'prison_id':           prison.id   if prison else None,
                    'prison_name':         prison.name if prison else '',
                    'prison_type':         getattr(prison, 'jail_type', '') or '',
                    'sanctioned_strength': getattr(v, 'sanctioned_strength', 0) or 0,
                    'occupied_count':      getattr(v, 'occupied_count', 0)      or 0,
                    'vacancy_count':       getattr(v, 'vacancy_count', 0)       or 0,
                })

            return self._json_response({'success': True, 'vacancies': data, 'prisons': data, 'data': data})

        except Exception as exc:
            _logger.exception('GET /api/transfer/vacancy-summary failed: %s', exc)
            return self._err('Internal server error', status=500)
