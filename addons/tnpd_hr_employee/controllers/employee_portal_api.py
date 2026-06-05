# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3
#
# Employee Self-Service Portal API
# Authentication: Odoo standard portal users (res.users + base.group_portal)
# Session: Standard Odoo session cookie (session_id) — same as admin portal
#
# Login flow:
#   1. Find hr.employee by x_employee_code
#   2. Auto-create res.users portal user if none linked (first login only)
#   3. request.session.authenticate() — Odoo sets session_id cookie
#   4. All subsequent requests validated via request.session.uid

import json
import logging
import re
from datetime import date

from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)


class EmployeePortalAPI(http.Controller):

    # ── Response helpers ──────────────────────────────────────────────────────

    def _json_response(self, data, status=200):
        origin = request.httprequest.headers.get('Origin', '*')
        return request.make_response(
            json.dumps(data, default=str),
            headers=[
                ('Content-Type',                     'application/json'),
                ('Access-Control-Allow-Origin',       origin),
                ('Access-Control-Allow-Credentials',  'true'),
                ('Access-Control-Allow-Headers',
                 'Content-Type, Authorization'),
                ('Access-Control-Allow-Methods',      'GET, POST, PUT, OPTIONS'),
            ],
            status=status,
        )

    def _ok(self, message='OK', **extra):
        payload = {'success': True, 'message': message}
        payload.update(extra)
        return self._json_response(payload)

    def _err(self, message, status=400):
        return self._json_response({'success': False, 'message': message}, status=status)

    def _parse_json_body(self):
        try:
            data = json.loads(request.httprequest.data or '{}')
            if not isinstance(data, dict):
                raise ValueError('Expected JSON object')
            return data, None
        except (json.JSONDecodeError, ValueError) as exc:
            return None, self._err(f'Invalid JSON: {exc}')

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def _setup_portal_user(self, user):
        """
        Ensure user has portal group and password set.
        Handles Odoo 19 where group_ids write must be done via direct SQL
        to avoid constraint ordering issues and auth='none' env limitations.
        """
        su_env = request.env(user=SUPERUSER_ID)

        # Set password directly via SQL — bypasses ORM compute/inverse chain
        ctx = su_env['res.users']._crypt_context()
        hashed_pw = ctx.hash('Welcome@123')
        su_env.cr.execute(
            'UPDATE res_users SET password=%s WHERE id=%s',
            (hashed_pw, user.id)
        )

        # Set portal group via direct SQL — avoids Odoo 19 constraint ordering issues
        # Get group IDs from ir.model.data
        su_env.cr.execute("""
            SELECT name, res_id FROM ir_model_data
            WHERE module='base' AND name IN ('group_portal','group_user','group_public')
        """)
        group_map = {row[0]: row[1] for row in su_env.cr.fetchall()}

        portal_gid   = group_map.get('group_portal')
        internal_gid = group_map.get('group_user')
        public_gid   = group_map.get('group_public')

        if portal_gid:
            # Remove all user-type groups, add portal group
            su_env.cr.execute(
                'DELETE FROM res_groups_users_rel WHERE uid=%s AND gid IN %s',
                (user.id, tuple(filter(None, [internal_gid, public_gid, portal_gid])))
            )
            su_env.cr.execute(
                'INSERT INTO res_groups_users_rel (uid, gid) VALUES (%s, %s) '
                'ON CONFLICT DO NOTHING',
                (user.id, portal_gid)
            )

        # Invalidate ORM cache and trigger recompute of stored compute fields
        user.invalidate_recordset()
        user._compute_share()
        _logger.info(
            'Portal user setup complete for %s (id=%d, share=%s)',
            user.login, user.id, user.share
        )

    def _get_portal_user_for_employee(self, emp):
        """
        Return the res.users portal account linked to emp.
        Auto-creates one with the default password on first login.
        Links it back to emp.user_id so the next call skips creation.
        Also ensures existing users have proper portal setup (password + group).
        """
        su_env = request.env(user=SUPERUSER_ID)

        # Check linked user
        if emp.user_id:
            user = emp.user_id
        else:
            # Find or create portal user
            existing = su_env['res.users'].search(
                [('login', '=', emp.x_employee_code)], limit=1
            )
            if existing:
                user = existing
                emp.with_env(su_env).write({'user_id': user.id})
            else:
                company_id = (
                    emp.company_id.id
                    or su_env['res.company'].search([], limit=1).id
                )
                user = su_env['res.users'].with_context(
                    no_reset_password=True,
                ).create({
                    'name':        emp.name,
                    'login':       emp.x_employee_code,
                    'email':       emp.work_email or f'{emp.x_employee_code}@tnpd.local',
                    'company_id':  company_id,
                    'company_ids': [(6, 0, [company_id])],
                })
                emp.with_env(su_env).write({'user_id': user.id})
                _logger.info(
                    'Portal user created for employee %s (id=%d)',
                    emp.x_employee_code, user.id
                )

        # Ensure portal group + password are set correctly
        # Check via SQL to avoid ORM cache issues
        su_env.cr.execute(
            'SELECT (password IS NOT NULL AND password != \'\') as has_pw '
            'FROM res_users WHERE id=%s',
            (user.id,)
        )
        row = su_env.cr.fetchone()
        has_password = row[0] if row else False

        # Check if user has portal group
        su_env.cr.execute("""
            SELECT 1 FROM res_groups_users_rel rgu
            JOIN ir_model_data imd ON imd.res_id = rgu.gid
            WHERE rgu.uid=%s AND imd.module='base' AND imd.name='group_portal'
        """, (user.id,))
        is_portal = bool(su_env.cr.fetchone())

        if not has_password or not is_portal:
            self._setup_portal_user(user)

        return user

    def _require_employee_session(self):
        """
        Validate the active Odoo session and return the linked hr.employee.
        Returns (emp, None) on success or (None, error_response) on failure.
        """
        uid = request.session.uid
        if not uid:
            return None, self._err('Authentication required', status=401)

        emp = request.env['hr.employee'].sudo().search(
            [('user_id', '=', uid), ('active', '=', True)], limit=1
        )
        if not emp:
            return None, self._err('No employee record linked to this session', status=401)
        return emp, None

    # ── Employee serialiser ───────────────────────────────────────────────────

    def _format_employee_profile(self, emp):
        def _d(d): return str(d) if d else ''
        def _s(s): return s if s else ''

        birthday_raw = ''
        try:
            emp.env.cr.execute(
                'SELECT birthday FROM hr_employee WHERE id = %s', (emp.id,)
            )
            row = emp.env.cr.fetchone()
            birthday_raw = str(row[0]) if row and row[0] else ''
        except Exception:
            birthday_raw = _d(emp.birthday)

        central  = emp.x_central_jail_id
        district = emp.x_district_jail_id
        sub      = emp.x_sub_jail_id

        current_posting = (
            (sub.name      if sub      else '')
            or (district.name if district else '')
            or (central.name  if central  else '')
            or _s(emp.x_sub_jail) or _s(emp.x_district_jail) or _s(emp.x_central_prison)
        ).strip()

        tenure_years = 0.0
        if emp.x_date_present_station:
            delta = date.today() - emp.x_date_present_station
            tenure_years = round(delta.days / 365.25, 1)

        return {
            'employee_code':                 _s(emp.x_employee_code),
            'name':                          _s(emp.name),
            'initial':                       _s(emp.x_initial),
            'designation':                   _s(emp.x_designation),
            'gender':                        _s(emp.sex),
            'dob':                           birthday_raw,
            'status':                        _s(emp.x_status or 'active'),
            'mobile_no':                     _s(emp.x_mobile_no),
            'mobile_cug_no':                 _s(emp.x_cug_mobile),
            'email':                         _s(emp.work_email),
            'date_of_appointment':           _d(emp.x_date_of_appointment),
            'date_of_promotion':             _d(emp.x_date_of_promotion),
            'date_of_retirement':            _d(emp.x_date_of_retirement),
            'working_since_present_station': _d(emp.x_date_present_station),
            'central_jail_id':               central.id or None,
            'central_jail_name':             _s(central.name),
            'district_jail_id':              district.id or None,
            'district_jail_name':            _s(district.name),
            'sub_jail_id':                   sub.id or None,
            'sub_jail_name':                 _s(sub.name),
            'current_posting':               current_posting,
            'tenure_years':                  tenure_years,
            'panel_year_sl_no':              _s(emp.x_panel_year_sl_no),
            'cps_no':                        _s(emp.x_cps_no),
            'gpf_no':                        _s(emp.x_gpf_no),
            'religion':                      _s(emp.x_religion),
            'community':                     _s(emp.x_community),
            'caste':                         _s(emp.x_caste),
            'mother_tongue':                 _s(emp.x_mother_tongue),
            'education_qualification':       _s(emp.x_education_qualification),
            'native_district':               _s(emp.x_native_district),
            'town':                          _s(emp.x_town),
            'taluk':                         _s(emp.x_taluk),
            'permanent_address':             _s(emp.x_permanent_address),
            'spouse_employment_details':     _s(emp.x_spouse_employment),
            'disciplinary_action_pending':   bool(emp.x_disciplinary_action_pending),
            'service_history_details':       _s(emp.x_service_history),
            'training_undergone':            _s(emp.x_training_undergone),
            'medals':                        _s(emp.x_medals),
            'rewards':                       _s(emp.x_rewards),
            'remarks':                       _s(emp.x_remarks),
        }

    def _format_transfer(self, rec, emp):
        from_sub      = rec.current_sub_jail.name       if rec.current_sub_jail       else ''
        from_district = rec.current_district_jail.name  if rec.current_district_jail  else ''
        from_central  = rec.current_central_prison.name if rec.current_central_prison else ''
        from_prison   = from_sub or from_district or from_central
        if not from_prison:
            from_prison = (
                (emp.x_sub_jail_id.name      if emp.x_sub_jail_id      else '')
                or (emp.x_district_jail_id.name if emp.x_district_jail_id else '')
                or (emp.x_central_jail_id.name  if emp.x_central_jail_id  else '')
                or ''
            )
        to_sub      = rec.requested_sub_jail.name       if rec.requested_sub_jail       else ''
        to_district = rec.requested_district_jail.name  if rec.requested_district_jail  else ''
        to_central  = rec.requested_central_prison.name if rec.requested_central_prison else ''
        to_prison   = to_sub or to_district or to_central or ''
        return {
            'request_id':       rec.id,
            'transfer_type':    rec.transfer_type or 'request',
            'transfer_reason':  rec.transfer_reason or '',
            'priority':         rec.priority or 'medium',
            'state':            rec.state,
            'from_prison':      from_prison,
            'to_prison':        to_prison,
            'to_central_name':  to_central,
            'to_district_name': to_district,
            'to_sub_name':      to_sub,
            'remarks':          rec.remarks or '',
            'request_date':     str(rec.create_date)   if rec.create_date   else '',
            'approved_date':    str(rec.approved_date) if rec.approved_date else '',
        }

    # ── POST /api/employee-portal/auth ────────────────────────────────────────

    @http.route(
        '/api/employee-portal/auth',
        auth='none', type='http', methods=['POST'], csrf=False,
    )
    def employee_login(self, **_kw):
        """
        Authenticate employee using Employee ID + password.

        First login:  auto-creates a res.users portal account for the employee.
        Every login:  delegates to request.session.authenticate() — Odoo sets
                      the session_id cookie; password verified via bcrypt.
        """
        data, err = self._parse_json_body()
        if err:
            return err

        employee_code = (data.get('employee_code') or '').strip()
        password      =  data.get('password') or ''

        if not employee_code:
            return self._err('Employee ID is required')
        if not password:
            return self._err('Password is required')

        emp = request.env['hr.employee'].sudo().search([
            ('x_employee_code', '=', employee_code),
            ('active', '=', True),
        ], limit=1)
        if not emp:
            return self._err('Invalid Employee ID or password', status=401)

        # Auto-create portal user on first login
        try:
            self._get_portal_user_for_employee(emp)
        except Exception as exc:
            _logger.exception('Failed to create portal user for %s', employee_code)
            return self._err('Login failed: unable to provision user account', status=500)

        # Standard Odoo 19 session authentication — sets session_id cookie
        # Odoo 19 signature: Session.authenticate(env, credential)
        # credential = {'type': 'password', 'login': ..., 'password': ...}
        try:
            auth_info = request.session.authenticate(
                request.env,
                {'type': 'password', 'login': employee_code, 'password': password},
            )
            uid = auth_info.get('uid') if isinstance(auth_info, dict) else auth_info
        except Exception as exc:
            _logger.info('Authentication failed for employee %s: %s', employee_code, exc)
            uid = None

        if not uid:
            return self._err('Invalid Employee ID or password', status=401)

        return self._ok('Login successful', employee=self._format_employee_profile(emp))

    # ── GET /api/employee-portal/whoami ──────────────────────────────────────

    @http.route(
        '/api/employee-portal/whoami',
        auth='none', type='http', methods=['GET'], csrf=False,
    )
    def employee_whoami(self, **_kw):
        """
        Return the employee profile for the current session.
        Used by EmployeeAuthContext on page load to restore session state.
        Returns 401 if no valid session exists.
        """
        emp, err = self._require_employee_session()
        if err:
            return err
        return self._ok(employee=self._format_employee_profile(emp))

    # ── POST /api/employee-portal/logout ─────────────────────────────────────

    @http.route(
        '/api/employee-portal/logout',
        auth='none', type='http', methods=['POST'], csrf=False,
    )
    def employee_logout(self, **_kw):
        """Destroy the Odoo session (server-side) and clear the session cookie."""
        request.session.logout(keep_db=True)
        return self._ok('Logged out successfully')

    # ── GET /api/employee-portal/profile ─────────────────────────────────────

    @http.route(
        '/api/employee-portal/profile',
        auth='none', type='http', methods=['GET'], csrf=False,
    )
    def get_profile(self, **_kw):
        emp, err = self._require_employee_session()
        if err:
            return err
        return self._ok(employee=self._format_employee_profile(emp))

    # ── PUT /api/employee-portal/profile ─────────────────────────────────────

    @http.route(
        '/api/employee-portal/profile',
        auth='none', type='http', methods=['PUT'], csrf=False,
    )
    def update_profile(self, **_kw):
        emp, err = self._require_employee_session()
        if err:
            return err

        data, err = self._parse_json_body()
        if err:
            return err

        mobile = (data.get('mobile') or '').strip()
        email  = (data.get('email')  or '').strip()

        if not mobile:
            return self._err('Mobile number is required')
        if not re.match(r'^[+]?[\d\s\-()/]{7,20}$', mobile):
            return self._err('Enter a valid mobile number')
        if not email:
            return self._err('Email address is required')
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return self._err('Enter a valid email address')

        emp.sudo().write({'x_mobile_no': mobile, 'work_email': email})
        return self._ok('Profile updated successfully')

    # ── GET /api/employee-portal/transfers ───────────────────────────────────

    @http.route(
        '/api/employee-portal/transfers',
        auth='none', type='http', methods=['GET'], csrf=False,
    )
    def get_transfers(self, page='1', limit='20', **_kw):
        emp, err = self._require_employee_session()
        if err:
            return err

        try:
            page  = max(1, int(page))
            limit = min(50, max(1, int(limit)))
        except ValueError:
            page, limit = 1, 20

        offset  = (page - 1) * limit
        TAR     = request.env['transfer.approval.request'].sudo()
        domain  = [('employee_id', '=', emp.id)]
        total   = TAR.search_count(domain)
        records = TAR.search(domain, limit=limit, offset=offset, order='create_date desc')

        return self._json_response({
            'success':   True,
            'transfers': [self._format_transfer(r, emp) for r in records],
            'total':     total,
            'page':      page,
            'limit':     limit,
        })

    # ── POST /api/employee-portal/transfers ──────────────────────────────────

    @http.route(
        '/api/employee-portal/transfers',
        auth='none', type='http', methods=['POST'], csrf=False,
    )
    def create_transfer(self, **_kw):
        emp, err = self._require_employee_session()
        if err:
            return err

        data, err = self._parse_json_body()
        if err:
            return err

        reason         = (data.get('transfer_reason') or '').strip()
        to_central_id  = data.get('to_central_jail_id')
        to_district_id = data.get('to_district_jail_id')
        to_sub_id      = data.get('to_sub_jail_id')

        if not reason:
            return self._err('Transfer reason is required')
        if not to_central_id:
            return self._err('Central Prison selection is required')
        if not to_sub_id:
            return self._err('Sub Jail selection is required')

        try:
            i_central  = int(to_central_id)
            i_sub      = int(to_sub_id)
            i_district = int(to_district_id) if to_district_id else False
        except (TypeError, ValueError):
            return self._err('Invalid jail ID')

        Jail = request.env['prison.jail'].sudo()
        if not Jail.browse(i_central).exists():
            return self._err('Central Prison not found')
        if not Jail.browse(i_sub).exists():
            return self._err('Sub Jail not found')

        # Prevent duplicate pending requests
        existing = request.env['transfer.approval.request'].sudo().search([
            ('employee_id', '=', emp.id),
            ('state', '=', 'pending'),
            ('active', '=', True),
        ], limit=1)
        if existing:
            return self._err(
                f'You already have a pending transfer request (Ref: TRF/{existing.id}). '
                f'Please wait for it to be processed before submitting a new one.'
            )

        try:
            admin_user = request.env.ref('base.user_admin')
        except Exception:
            admin_user = request.env['res.users'].sudo().search(
                [('active', '=', True), ('share', '=', False)], limit=1
            )

        vals = {
            'employee_id':             emp.id,
            'transfer_type':           'request',
            'transfer_reason':         reason,
            'priority':                data.get('priority') or 'medium',
            'state':                   'pending',
            'approval_user_id':        admin_user.id,
            'requested_central_prison': i_central,
            'requested_district_jail': i_district or False,
            'requested_sub_jail':      i_sub,
            'current_central_prison':  emp.x_central_jail_id.id if emp.x_central_jail_id else False,
            'current_district_jail':   emp.x_district_jail_id.id if emp.x_district_jail_id else False,
            'current_sub_jail':        emp.x_sub_jail_id.id if emp.x_sub_jail_id else False,
        }

        try:
            TAR = request.env['transfer.approval.request'].sudo()
            rec = TAR.with_context(mail_notrack=True).create(vals)

            request.env['tnpd.notification'].sudo().create({
                'employee_id':         emp.id,
                'transfer_request_id': rec.id,
                'notification_type':   'transfer_pending',
                'action_type':         'transfer_submitted',
                'message': (
                    f'Your transfer request (Ref: TRF/{rec.id}) has been submitted '
                    f'successfully and is pending review.'
                ),
            })
            return self._ok('Transfer request submitted successfully', request_id=rec.id)
        except Exception as exc:
            _logger.exception('Error creating employee transfer request')
            return self._err(str(exc))

    # ── GET /api/employee-portal/notifications ───────────────────────────────

    @http.route(
        '/api/employee-portal/notifications',
        auth='none', type='http', methods=['GET'], csrf=False,
    )
    def get_notifications(self, page='1', limit='20', **_kw):
        emp, err = self._require_employee_session()
        if err:
            return err

        try:
            page  = max(1, int(page))
            limit = min(50, max(1, int(limit)))
        except ValueError:
            page, limit = 1, 20

        offset       = (page - 1) * limit
        Notif        = request.env['tnpd.notification'].sudo()
        domain       = [('employee_id', '=', emp.id)]
        total        = Notif.search_count(domain)
        unread_count = Notif.search_count(domain + [('is_read', '=', False)])
        records      = Notif.search(domain, limit=limit, offset=offset, order='sent_date desc')

        def _fmt(n):
            return {
                'id':                  n.id,
                'notification_type':   n.notification_type,
                'action_type':         n.action_type or '',
                'message':             n.message,
                'sent_date':           str(n.sent_date) if n.sent_date else '',
                'is_read':             n.is_read,
                'transfer_request_id': n.transfer_request_id.id if n.transfer_request_id else None,
            }

        return self._json_response({
            'success':       True,
            'notifications': [_fmt(n) for n in records],
            'total':         total,
            'unread_count':  unread_count,
            'page':          page,
            'limit':         limit,
        })

    # ── POST /api/employee-portal/notifications/mark-read ────────────────────

    @http.route(
        '/api/employee-portal/notifications/mark-read',
        auth='none', type='http', methods=['POST'], csrf=False,
    )
    def mark_notifications_read(self, **_kw):
        emp, err = self._require_employee_session()
        if err:
            return err

        data, err = self._parse_json_body()
        if err:
            return err

        Notif           = request.env['tnpd.notification'].sudo()
        notification_id = data.get('notification_id')

        if notification_id:
            notif = Notif.search([
                ('id', '=', int(notification_id)),
                ('employee_id', '=', emp.id),
            ], limit=1)
            if notif:
                notif.mark_as_read()
        else:
            Notif.search([
                ('employee_id', '=', emp.id),
                ('is_read', '=', False),
            ]).mark_as_read()

        return self._ok('Notifications marked as read')

    # ── POST /api/employee-portal/change-password ─────────────────────────────

    @http.route(
        '/api/employee-portal/change-password',
        auth='none', type='http', methods=['POST'], csrf=False,
    )
    def change_password(self, **_kw):
        emp, err = self._require_employee_session()
        if err:
            return err

        data, err = self._parse_json_body()
        if err:
            return err

        current_pw = data.get('current_password') or ''
        new_pw     = data.get('new_password')     or ''

        if not current_pw:
            return self._err('Current password is required')
        if not new_pw:
            return self._err('New password is required')
        if len(new_pw) < 8:
            return self._err('New password must be at least 8 characters')
        if current_pw == new_pw:
            return self._err('New password must be different from the current password')

        # Verify current password using Odoo internal check (Odoo 19 signature)
        try:
            request.env['res.users'].sudo()._check_credentials(current_pw, {'interactive': False})
            uid_check = True
        except Exception:
            uid_check = False

        if not uid_check:
            return self._err('Current password is incorrect', status=401)

        # Change password — Odoo stores as bcrypt hash
        emp.user_id.sudo().write({'password': new_pw})
        return self._ok('Password changed successfully')

    # ── POST /api/admin/bulk-create-portal-users ──────────────────────────────

    @http.route(
        '/api/admin/bulk-create-portal-users',
        auth='none', type='http', methods=['POST'], csrf=False,
    )
    def bulk_create_portal_users(self, **_kw):
        """
        One-time admin endpoint to pre-create Odoo portal users for ALL
        active employees who do not yet have a portal account.

        Protected by admin Odoo session (is_admin check).

        Response
        --------
        {
          "success": true,
          "created": 42,
          "skipped": 6,
          "failed":  0,
          "details": [
            {"code": "EMP001", "name": "...", "status": "created"},
            ...
          ]
        }
        """
        # Require active Odoo session
        uid = request.session.uid
        if not uid:
            return self._err('Authentication required', status=401)

        # Require admin user
        user = request.env['res.users'].sudo().browse(uid)
        if not user.exists() or not user._is_admin():
            return self._err('Admin access required', status=403)

        su_env = request.env(user=SUPERUSER_ID)

        employees = su_env['hr.employee'].search([
            ('active',          '=', True),
            ('x_employee_code', '!=', False),
            ('x_employee_code', '!=', ''),
        ])

        created = 0
        skipped = 0
        failed  = 0
        details = []

        # Pre-fetch group IDs once via SQL
        su_env.cr.execute("""
            SELECT name, res_id FROM ir_model_data
            WHERE module='base' AND name IN ('group_portal','group_user','group_public')
        """)
        group_map    = {row[0]: row[1] for row in su_env.cr.fetchall()}
        portal_gid   = group_map.get('group_portal')
        internal_gid = group_map.get('group_user')
        public_gid   = group_map.get('group_public')
        all_type_gids = tuple(filter(None, [portal_gid, internal_gid, public_gid]))

        ctx       = su_env['res.users']._crypt_context()
        hashed_pw = ctx.hash('Welcome@123')

        for emp in employees:
            code = emp.x_employee_code
            name = emp.name or ''
            try:
                # Already has a linked portal user — skip
                if emp.user_id:
                    su_env.cr.execute(
                        'SELECT 1 FROM res_groups_users_rel '
                        'WHERE uid=%s AND gid=%s',
                        (emp.user_id.id, portal_gid)
                    )
                    if su_env.cr.fetchone():
                        skipped += 1
                        details.append({'code': code, 'name': name, 'status': 'skipped'})
                        continue

                # Re-use orphaned user with same login
                su_env.cr.execute(
                    'SELECT id FROM res_users WHERE login=%s LIMIT 1', (code,)
                )
                row = su_env.cr.fetchone()
                if row:
                    user_id = row[0]
                    emp.write({'user_id': user_id})
                else:
                    company_id = (
                        emp.company_id.id
                        or su_env['res.company'].search([], limit=1).id
                    )
                    new_user = su_env['res.users'].with_context(
                        no_reset_password=True
                    ).create({
                        'name':        name,
                        'login':       code,
                        'email':       emp.work_email or f'{code}@tnpd.local',
                        'company_id':  company_id,
                        'company_ids': [(6, 0, [company_id])],
                    })
                    user_id = new_user.id
                    emp.write({'user_id': user_id})

                # Set password via SQL (bypasses ORM compute/inverse chain)
                su_env.cr.execute(
                    'UPDATE res_users SET password=%s WHERE id=%s',
                    (hashed_pw, user_id)
                )

                # Assign portal group via SQL (Odoo 19 constraint workaround)
                if all_type_gids:
                    su_env.cr.execute(
                        'DELETE FROM res_groups_users_rel WHERE uid=%s AND gid IN %s',
                        (user_id, all_type_gids)
                    )
                su_env.cr.execute(
                    'INSERT INTO res_groups_users_rel (uid, gid) VALUES (%s, %s) '
                    'ON CONFLICT DO NOTHING',
                    (user_id, portal_gid)
                )

                created += 1
                details.append({'code': code, 'name': name, 'status': 'created'})

            except Exception as exc:
                _logger.exception(
                    'bulk_create_portal_users: failed for %s — %s', code, exc
                )
                failed += 1
                details.append({
                    'code': code, 'name': name,
                    'status': 'failed', 'error': str(exc),
                })

        _logger.info(
            'bulk_create_portal_users: created=%d skipped=%d failed=%d',
            created, skipped, failed
        )
        return self._json_response({
            'success': True,
            'created': created,
            'skipped': skipped,
            'failed':  failed,
            'details': details,
        })

    # ── POST /api/admin/bulk-create-portal-users/safe ─────────────────────────

    @http.route(
        '/api/admin/bulk-create-portal-users/safe',
        auth='none', type='http', methods=['POST'], csrf=False,
    )
    def bulk_create_portal_users_safe(self, **_kw):
        """Same as bulk_create_portal_users but wraps everything in try/except
        and returns any top-level error as JSON instead of 500."""
        try:
            return self.bulk_create_portal_users(**_kw)
        except Exception as exc:
            _logger.exception('bulk_create_portal_users_safe top-level error')
            return self._json_response({
                'success': False,
                'error':   str(exc),
                'type':    type(exc).__name__,
            }, status=200)
