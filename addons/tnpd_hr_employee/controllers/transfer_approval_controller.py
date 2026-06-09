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

        # ── Flatten current posting (Sub > District > Central) ──────────────
        from_sub      = rec.current_sub_jail.name      if rec.current_sub_jail      else ''
        from_district = rec.current_district_jail.name if rec.current_district_jail else ''
        from_central  = rec.current_central_prison.name if rec.current_central_prison else ''
        from_prison_name = from_sub or from_district or from_central or ''

        # Fallback: snapshot fields empty → read from employee's current legacy
        # text fields (covers employees imported before the jail hierarchy was added)
        if not from_prison_name:
            emp = rec.employee_id
            from_prison_name = (
                (emp.x_sub_jail_id.name if emp.x_sub_jail_id else '')
                or (emp.x_district_jail_id.name if emp.x_district_jail_id else '')
                or (emp.x_central_jail_id.name if emp.x_central_jail_id else '')
                or emp.x_sub_jail or emp.x_district_jail or emp.x_central_prison
                or ''
            ).strip()

        # ── Flatten requested destination (Sub > District > Central) ────────
        to_sub      = rec.requested_sub_jail.name      if rec.requested_sub_jail      else ''
        to_district = rec.requested_district_jail.name if rec.requested_district_jail else ''
        to_central  = rec.requested_central_prison.name if rec.requested_central_prison else ''
        to_prison_name = to_sub or to_district or to_central or ''

        return {
            'request_id':               rec.id,
            'employee_id':              rec.employee_id.id,
            'employee_name':            rec.employee_id.name or '',
            'employee_code':            rec.employee_id.x_employee_code or '',
            'designation':              rec.employee_id.x_designation or '',
            # Current posting snapshot — nested objects (for detail view)
            'current_central_prison':   self._format_jail(rec.current_central_prison),
            'current_district_jail':    self._format_jail(rec.current_district_jail),
            'current_sub_jail':         self._format_jail(rec.current_sub_jail),
            # Current posting — flat strings (for list/table display)
            'from_prison_name':         from_prison_name,
            'from_central_name':        from_central,
            'from_district_name':       from_district,
            'from_sub_name':            from_sub,
            # Requested destination — nested objects (for detail view)
            'requested_central_prison': self._format_jail(rec.requested_central_prison),
            'requested_district_jail':  self._format_jail(rec.requested_district_jail),
            'requested_sub_jail':       self._format_jail(rec.requested_sub_jail),
            # Requested destination — flat strings (for list/table display)
            'to_prison_name':           to_prison_name,
            'to_central_name':          to_central,
            'to_district_name':         to_district,
            'to_sub_name':              to_sub,
            # Preferences 2 & 3
            'preference_2': {
                'central': self._format_jail(getattr(rec, 'preference_2_central_prison', False)),
                'district': self._format_jail(getattr(rec, 'preference_2_district_jail', False)),
                'sub':      self._format_jail(getattr(rec, 'preference_2_sub_jail', False)),
            },
            'preference_3': {
                'central': self._format_jail(getattr(rec, 'preference_3_central_prison', False)),
                'district': self._format_jail(getattr(rec, 'preference_3_district_jail', False)),
                'sub':      self._format_jail(getattr(rec, 'preference_3_sub_jail', False)),
            },
            # Workflow
            'state':          rec.state,
            'requested_by':   rec.requested_by.name or '',
            'approval_user':  {'id': rec.approval_user_id.id, 'name': rec.approval_user_id.name or ''},
            'approved_by':    rec.approved_by.name or '',
            'approved_date':  str(rec.approved_date) if rec.approved_date else '',
            'remarks':        rec.remarks or '',
            'create_date':    str(rec.create_date) if rec.create_date else '',
            'request_date':   str(rec.create_date) if rec.create_date else '',
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
            employee = self._resolve_employee(env, data['employee_id'])
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
    # VACANCY HELPER
    # ==================================================================

    def _resolve_employee(self, env, employee_id_raw):
        """
        Resolve an employee from either:
          • an x_employee_code string  (e.g. "24010985327")  ← sent by the frontend
          • an Odoo internal record ID (e.g. 2085)           ← legacy callers

        Returns the hr.employee recordset (may be empty — caller must check .exists()).
        """
        Employee = env['hr.employee'].sudo()
        raw = str(employee_id_raw).strip()

        # Try x_employee_code lookup first (handles string codes from the Personnel API)
        if raw:
            emp = Employee.search([('x_employee_code', '=', raw)], limit=1)
            if emp:
                return emp

        # Fall back: try integer browse (handles callers that pass the DB id)
        try:
            emp = Employee.browse(int(raw))
            return emp  # caller checks .exists()
        except (ValueError, TypeError):
            pass

        return Employee  # empty recordset

    def _get_vacancy_record(self, env, prison_id):
        """
        Return the active prison.vacancy record for the given prison.jail id.

        Walks up the jail hierarchy (sub → district → central) so that a
        transfer to a sub-jail still finds the parent prison's vacancy record
        when no dedicated sub-jail record exists.

        Returns None if the prison.vacancy model is not installed or no record
        exists anywhere in the hierarchy.
        """
        try:
            Vacancy  = env['prison.vacancy'].sudo()
            PrisonJail = env['prison.jail'].sudo()

            jail_id = prison_id
            visited = set()                    # guard against circular refs
            while jail_id and jail_id not in visited:
                visited.add(jail_id)
                rec = Vacancy.search(
                    [('prison_id', '=', jail_id), ('active', '=', True)],
                    limit=1,
                )
                if rec:
                    return rec
                jail = PrisonJail.browse(jail_id)
                if jail.exists() and jail.parent_id:
                    jail_id = jail.parent_id.id
                else:
                    break
            return None
        except Exception:
            return None

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

        Pre-condition (vacancy check):
        • The requested sub jail must have at least one vacant position in the
          prison.vacancy master.  If not, a 400 response is returned with
          ``vacancy_error: true`` so the front-end can display a specific message.

        On approval:
        • Employee's x_central_jail_id / x_district_jail_id / x_sub_jail_id
          (Many2one) fields are updated to the requested jail records.
        • Legacy Char fields (x_central_prison / x_district_jail / x_sub_jail)
          are also synced for backward compatibility.
        • x_date_present_station is set to today.
        • A dated entry is prepended to x_service_history.
        • The vacancy_count of the target prison is decremented by 1.

        Body (JSON)
        -----------
        request_id  int     required
        remarks     string  required  (approval remarks, mandatory)
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

            approval_remarks = (data.get('remarks') or '').strip()
            if not approval_remarks:
                return self._err('Approval remarks are required.')

            env = request.env(user=uid)

            tar = env['transfer.approval.request'].sudo().browse(
                int(data['request_id'])
            )
            if not tar.exists():
                return self._err('Transfer request not found', status=404)

            # Allow approval by: the designated approver OR any HR admin.
            approval_uid = tar.approval_user_id.id if tar.approval_user_id else None
            if approval_uid and approval_uid != uid:
                try:
                    is_hr = env['res.users'].sudo().browse(uid).has_group('hr.group_hr_user')
                except Exception:
                    is_hr = False
                if not is_hr:
                    return self._err(
                        'You are not authorised to approve this request',
                        status=403,
                    )

            if tar.state != 'pending':
                return self._err(
                    f'Request is already {tar.state} and cannot be approved'
                )

            # --- Vacancy check: target sub jail must have vacancies --------
            target_prison_id = tar.requested_sub_jail.id if tar.requested_sub_jail else None
            vacancy_rec = self._get_vacancy_record(env, target_prison_id) if target_prison_id else None
            if vacancy_rec is not None and vacancy_rec.exists():
                if not vacancy_rec.is_vacancy_available():
                    return self._json_response({
                        'success': False,
                        'message': 'No vacancy is currently available in the requested prison.',
                        'vacancy_error': True,
                        'prison_name': vacancy_rec.prison_name or tar.requested_sub_jail.name or '',
                        'vacancy_count': vacancy_rec.vacancy_count,
                    }, status=400)

            emp = tar.employee_id.sudo()
            approved_date_now = fields.Datetime.now()
            approved_by_user  = env['res.users'].sudo().browse(uid)

            self._apply_transfer_to_employee(
                emp, tar,
                approved_by_user=approved_by_user,
                approved_date_now=approved_date_now,
                note_prefix='Transfer Approved',
            )

            tar.sudo().write({
                'state':         'approved',
                'approved_by':   uid,
                'approved_date': approved_date_now,
                'remarks':       approval_remarks,
            })

            # --- Decrement vacancy count at target prison ------------------
            if vacancy_rec is not None and vacancy_rec.exists():
                new_count = max(0, vacancy_rec.vacancy_count - 1)
                new_occupied = vacancy_rec.occupied_count + 1
                vacancy_rec.sudo().write({
                    'vacancy_count':  new_count,
                    'occupied_count': new_occupied,
                })
                _logger.info(
                    'Vacancy decremented for prison_id=%d: vacancy_count=%d → %d',
                    target_prison_id, vacancy_rec.vacancy_count + 1, new_count,
                )

            _logger.info(
                'Transfer request %d approved by user=%d; employee=%d',
                tar.id, uid, emp.id,
            )

            # ── Send notification to employee portal ──────────────────────
            try:
                to_jail = (
                    tar.requested_sub_jail.name
                    or tar.requested_district_jail.name
                    or tar.requested_central_prison.name
                    or 'the requested posting'
                )
                env['tnpd.notification'].sudo().create({
                    'employee_id':         emp.id,
                    'transfer_request_id': tar.id,
                    'notification_type':   'transfer_approved',
                    'action_type':         'transfer_approved',
                    'message': (
                        f'Your transfer request (Ref: TRF/{tar.id}) has been approved. '
                        f'You have been transferred to {to_jail}. '
                        f'Approved by: {approved_by_user.name}.'
                    ),
                    'sent_by': approved_by_user.id,
                })
            except Exception as notif_exc:
                _logger.warning('Failed to send approval notification: %s', notif_exc)

            # --- Build updated employee info for response ------------------
            emp_info = {
                'employee_id':   emp.id,
                'employee_name': emp.name or '',
                'employee_code': emp.x_employee_code or '',
                'designation':   emp.x_designation or '',
                'current_central_prison': {
                    'id':   emp.x_central_jail_id.id if emp.x_central_jail_id else None,
                    'name': emp.x_central_jail_id.name if emp.x_central_jail_id else emp.x_central_prison or '',
                },
                'current_district_jail': {
                    'id':   emp.x_district_jail_id.id if emp.x_district_jail_id else None,
                    'name': emp.x_district_jail_id.name if emp.x_district_jail_id else emp.x_district_jail or '',
                },
                'current_sub_jail': {
                    'id':   emp.x_sub_jail_id.id if emp.x_sub_jail_id else None,
                    'name': emp.x_sub_jail_id.name if emp.x_sub_jail_id else emp.x_sub_jail or '',
                },
                'date_present_station': str(emp.x_date_present_station) if emp.x_date_present_station else '',
            }

            return self._ok('Transfer approved successfully', employee=emp_info)

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
        remarks     str  optional  (rejection reason — stored in the remarks field)

        The rejection actor and timestamp are stored in the shared
        ``approved_by`` / ``approved_date`` fields (same pattern as the
        approve flow; the ``state`` field disambiguates the action).
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

            # Allow rejection by: the designated approver OR any HR admin.
            # The UI already restricts this action to admin users.
            approval_uid = tar.approval_user_id.id if tar.approval_user_id else None
            if approval_uid and approval_uid != uid:
                try:
                    is_hr = env['res.users'].sudo().browse(uid).has_group('hr.group_hr_user')
                except Exception:
                    is_hr = False
                if not is_hr:
                    return self._err(
                        'You are not authorised to reject this request',
                        status=403,
                    )

            if tar.state != 'pending':
                return self._err(
                    f'Request is already {tar.state} and cannot be rejected'
                )

            rejected_date = fields.Datetime.now()
            rejecting_user = env['res.users'].sudo().browse(uid)

            # Build rejection remarks: prefix with rejector name and timestamp
            # so the audit trail is self-contained even without a separate field.
            raw_remarks = (data.get('remarks') or '').strip()
            rejection_note = (
                f"[Rejected on {rejected_date.strftime('%d-%b-%Y %H:%M')} "
                f"by {rejecting_user.name}]"
            )
            if raw_remarks:
                rejection_note = f"{rejection_note}\n{raw_remarks}"

            # Merge with any existing remarks so prior notes are preserved.
            existing_remarks = (tar.remarks or '').strip()
            merged_remarks = (
                rejection_note + '\n' + existing_remarks
                if existing_remarks
                else rejection_note
            )

            update_vals = {
                'state':         'rejected',
                # approved_by / approved_date are the shared "actioned_by" fields;
                # state='rejected' disambiguates this from an approval.
                'approved_by':   uid,
                'approved_date': rejected_date,
                'remarks':       merged_remarks,
            }

            tar.sudo().write(update_vals)

            _logger.info(
                'Transfer request %d rejected by user=%d (%s)',
                tar.id, uid, rejecting_user.name,
            )

            # ── Send notification to employee portal ──────────────────────
            try:
                rejection_reason = raw_remarks or 'No reason provided.'
                env['tnpd.notification'].sudo().create({
                    'employee_id':         tar.employee_id.id,
                    'transfer_request_id': tar.id,
                    'notification_type':   'transfer_rejected',
                    'action_type':         'transfer_rejected',
                    'message': (
                        f'Your transfer request (Ref: TRF/{tar.id}) has been rejected. '
                        f'Reason: {rejection_reason}'
                    ),
                    'sent_by': rejecting_user.id,
                })
            except Exception as notif_exc:
                _logger.warning('Failed to send rejection notification: %s', notif_exc)

            return self._ok(
                'Transfer request rejected successfully',
                request_id=tar.id,
                rejected_by=rejecting_user.name,
                rejected_date=str(rejected_date),
                remarks=merged_remarks,
            )

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
            employee = self._resolve_employee(env, data['employee_id'])
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

            # Check vacancy at OTHER prisons (not current sub jail) and collect details
            emp_vacancy = has_any_vacancy  # simplified: any vacancy anywhere
            vacancy_detail = None  # full vacancy info for the current posting
            try:
                if emp.x_sub_jail_id:
                    vacancy_elsewhere = env['prison.vacancy'].sudo().search([
                        ('vacancy_count', '>', 0),
                        ('prison_id', '!=', emp.x_sub_jail_id.id),
                    ], limit=1)
                    emp_vacancy = bool(vacancy_elsewhere)
                    # Current prison vacancy detail
                    current_vac = env['prison.vacancy'].sudo().search([
                        ('prison_id', '=', emp.x_sub_jail_id.id),
                        ('active', '=', True),
                    ], limit=1)
                    if current_vac:
                        vacancy_detail = {
                            'prison_id':          current_vac.prison_id.id if current_vac.prison_id else None,
                            'prison_name':        current_vac.prison_name or '',
                            'sanctioned_strength': current_vac.sanctioned_strength or 0,
                            'filled_positions':   current_vac.occupied_count or 0,
                            'vacant_positions':   current_vac.vacancy_count or 0,
                            'vacancy_available':  (current_vac.vacancy_count or 0) > 0,
                        }
            except Exception:
                pass

            # Resolve prison names: Many2one takes priority, legacy Char as fallback
            # (mirrors the fix in employee_api._format_employee)
            central_name  = (emp.x_central_jail_id.name  if emp.x_central_jail_id  else '') or emp.x_central_prison  or ''
            district_name = (emp.x_district_jail_id.name if emp.x_district_jail_id else '') or emp.x_district_jail   or ''
            sub_name      = (emp.x_sub_jail_id.name      if emp.x_sub_jail_id      else '') or emp.x_sub_jail         or ''

            data.append({
                'employee_id':      emp.id,
                'employee_name':    emp.name or '',
                'employee_code':    emp.x_employee_code or '',
                'designation':      emp.x_designation or '',
                'rank':             emp.job_id.name if emp.job_id else '',
                # Prison fields with legacy fallback — same priority as Personnel module
                'current_central_prison': {
                    'id':   emp.x_central_jail_id.id if emp.x_central_jail_id else None,
                    'name': central_name,
                },
                'current_district_jail': {
                    'id':   emp.x_district_jail_id.id if emp.x_district_jail_id else None,
                    'name': district_name,
                },
                'current_sub_jail': {
                    'id':   emp.x_sub_jail_id.id if emp.x_sub_jail_id else None,
                    'name': sub_name,
                },
                'date_present_station':   str(emp.x_date_present_station),
                'tenure_years':           tenure_years,
                'is_eligible':            True,
                'has_vacancy_elsewhere':  emp_vacancy,
                # Vacancy details for current posting (None if prison.vacancy not installed)
                'current_prison_vacancy': vacancy_detail,
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

            employee = self._resolve_employee(env, data['employee_id'])
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
    # INTERNAL: Serialize a prison.vacancy record
    # ==================================================================

    def _format_vacancy(self, v):
        """Serialize one prison.vacancy record to the standard API shape."""
        prison = v.prison_id
        sanctioned  = v.sanctioned_strength or 0
        occupied    = v.occupied_count      or 0
        vacant      = v.vacancy_count       or 0
        return {
            'prison_id':          prison.id   if prison else None,
            'prison_name':        v.prison_name or (prison.name if prison else ''),
            'prison_type':        v.prison_type or (prison.jail_type if prison else ''),
            'prison_code':        v.prison_code or '',
            'sanctioned_strength': sanctioned,
            'filled_positions':   occupied,
            'vacant_positions':   vacant,
            # Legacy / alternative key names kept for backwards compatibility
            'occupied_count':     occupied,
            'vacancy_count':      vacant,
            'vacancy_available':  vacant > 0,
        }

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
                    "prison_name": "Central Prison Chennai",
                    "prison_type": "central_prison",
                    "prison_code": "CPC",
                    "sanctioned_strength": 120,
                    "filled_positions": 117,
                    "vacant_positions": 3,
                    "vacancy_available": true
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
                vacancies = env['prison.vacancy'].sudo().search(
                    [('active', '=', True)],
                    order='prison_type, prison_name',
                )
            except Exception as exc:
                _logger.warning('prison.vacancy model not found: %s', exc)
                return self._json_response({
                    'success': True,
                    'data': [],
                    'vacancies': [],
                    'prisons': [],
                    'note': 'prison.vacancy model is not installed',
                })

            data = [self._format_vacancy(v) for v in vacancies]

            # Summary counts
            total_sanctioned = sum(d['sanctioned_strength'] for d in data)
            total_filled     = sum(d['filled_positions']    for d in data)
            total_vacant     = sum(d['vacant_positions']    for d in data)

            return self._json_response({
                'success':  True,
                'data':     data,
                'vacancies': data,
                'prisons':  data,
                'summary': {
                    'total_prisons':          len(data),
                    'prisons_with_vacancy':   sum(1 for d in data if d['vacancy_available']),
                    'total_sanctioned':       total_sanctioned,
                    'total_filled':           total_filled,
                    'total_vacant':           total_vacant,
                },
            })

        except Exception as exc:
            _logger.exception('GET /api/transfer/vacancy-summary failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 13 – Single-Prison Vacancy Check
    # GET /api/transfer/vacancy-check?prison_id=<id>
    # ==================================================================

    @http.route(
        '/api/transfer/vacancy-check',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def vacancy_check(self, **kwargs):
        """
        Return vacancy information for a single prison (real-time check).

        Query params
        ------------
        prison_id  int  required  (prison.jail id)

        Response
        --------
        {
            "success": true,
            "prison_id": 1,
            "prison_name": "...",
            "sanctioned_strength": 50,
            "filled_positions": 47,
            "vacant_positions": 3,
            "vacancy_available": true
        }
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            prison_id_raw = kwargs.get('prison_id')
            if not prison_id_raw:
                return self._err('Missing required query parameter: prison_id')

            try:
                prison_id = int(prison_id_raw)
            except (TypeError, ValueError):
                return self._err('prison_id must be an integer')

            env = request.env(user=uid)

            # Validate the prison.jail record exists
            jail = env['prison.jail'].sudo().browse(prison_id)
            if not jail.exists():
                return self._err(f'Prison not found: prison_id={prison_id}', status=404)

            vacancy_rec = self._get_vacancy_record(env, prison_id)
            if vacancy_rec is None or not vacancy_rec.exists():
                # No vacancy record — return unknown status, not an error
                return self._json_response({
                    'success':           True,
                    'prison_id':         prison_id,
                    'prison_name':       jail.name or '',
                    'prison_type':       jail.jail_type or '',
                    'sanctioned_strength': 0,
                    'filled_positions':  0,
                    'vacant_positions':  0,
                    'occupied_count':    0,
                    'vacancy_count':     0,
                    'vacancy_available': False,
                    'note':              'No vacancy record found for this prison.',
                })

            formatted = self._format_vacancy(vacancy_rec)
            return self._json_response({'success': True, **formatted})

        except Exception as exc:
            _logger.exception('GET /api/transfer/vacancy-check failed: %s', exc)
            return self._err('Internal server error', status=500)

    # ==================================================================
    # API 14 – Send / Store Notification
    # POST /api/notifications/send
    # ==================================================================

    @http.route(
        '/api/notifications/send',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def send_notification(self, **_kwargs):
        """
        Create and store a notification record against an employee.

        Body (JSON)
        -----------
        employee_id          str  required  employee x_employee_code
        message              str  required  notification text
        notification_type    str  optional  one of: no_vacancy | transfer_approved |
                                            transfer_rejected | transfer_pending | general
        action_type          str  optional  machine-readable key, e.g. transfer_approval_no_vacancy
        transfer_request_id  int  optional  related transfer.approval.request id

        Response
        --------
        {
          "success": true,
          "notification_id": <int>,
          "employee_name": "<str>",
          "employee_code": "<str>",
          "notification_type": "<str>",
          "action_type": "<str>",
          "message": "<str>",
          "sent_date": "<datetime str>"
        }
        """
        try:
            uid, err = self._require_auth()
            if err:
                return err

            data, err = self._parse_json_body()
            if err:
                return err

            # ── Validate required fields ──────────────────────────────────
            if not data.get('employee_id'):
                return self._err('Missing required field: employee_id')
            if not data.get('message', '').strip():
                return self._err('Missing required field: message')

            env = request.env(user=uid)

            # ── Resolve employee ──────────────────────────────────────────
            employee = self._resolve_employee(env, data['employee_id'])
            if not employee.exists():
                return self._err('Employee not found', status=404)

            # ── Build notification vals ───────────────────────────────────
            notification_type = data.get('notification_type', 'general')
            valid_types = {'no_vacancy', 'transfer_approved', 'transfer_rejected',
                           'transfer_pending', 'general'}
            if notification_type not in valid_types:
                notification_type = 'general'

            vals = {
                'employee_id':       employee.id,
                'message':           data['message'].strip(),
                'notification_type': notification_type,
                'action_type':       (data.get('action_type') or '').strip() or False,
                'sent_by':           uid,
            }

            # Optionally link to a transfer request
            req_id = data.get('transfer_request_id')
            if req_id:
                try:
                    tar = env['transfer.approval.request'].sudo().browse(int(req_id))
                    if tar.exists():
                        vals['transfer_request_id'] = tar.id
                except (TypeError, ValueError):
                    pass

            # ── Create ────────────────────────────────────────────────────
            notif = env['tnpd.notification'].sudo().create(vals)

            _logger.info(
                'Notification %d created: type=%s action=%s employee=%s by user=%d',
                notif.id, notification_type, vals.get('action_type', '-'),
                employee.x_employee_code, uid,
            )

            return self._json_response({
                'success':           True,
                'notification_id':   notif.id,
                'employee_name':     employee.name or '',
                'employee_code':     employee.x_employee_code or '',
                'notification_type': notif.notification_type,
                'action_type':       notif.action_type or '',
                'message':           notif.message,
                'sent_date':         str(notif.sent_date),
            }, status=201)

        except Exception as exc:
            _logger.exception('POST /api/notifications/send failed: %s', exc)
            return self._err('Internal server error', status=500)
