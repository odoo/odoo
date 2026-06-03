# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

"""
Settings REST API
=================

Auth: all endpoints require a valid Odoo user session (auth='none' + _require_auth).

Endpoints
---------
GET  /api/profile               — Fetch logged-in user's profile
PUT  /api/profile               — Update mobile / email
POST /api/change-password       — Change password with policy enforcement
"""

import json
import logging
import re

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)

# Password policy
_PW_MIN_LEN  = 8
_PW_UPPER    = re.compile(r'[A-Z]')
_PW_LOWER    = re.compile(r'[a-z]')
_PW_DIGIT    = re.compile(r'[0-9]')
_PW_SPECIAL  = re.compile(r'[^A-Za-z0-9]')
_EMAIL_RE    = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_MOBILE_RE   = re.compile(r'^[+]?[\d\s\-()]{7,20}$')


class SettingsApiController(http.Controller):

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _json(self, data, status=200):
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _ok(self, data):
        return self._json({'success': True, **data})

    def _err(self, message, status=400):
        return self._json({'success': False, 'message': message}, status=status)

    def _require_auth(self):
        uid = request.session.uid
        if not uid:
            return None, self._json(
                {'success': False, 'message': 'Authentication required'}, status=401
            )
        return uid, None

    def _parse_body(self):
        try:
            body = request.httprequest.get_data(as_text=True)
            return json.loads(body) if body else {}
        except Exception:
            return None

    def _get_role(self, user):
        try:
            if user.has_group('base.group_system'):
                return 'Super Admin'
            if user.has_group('base.group_erp_manager'):
                return 'Admin'
        except Exception:
            pass
        return 'User'

    # ── GET /api/profile ──────────────────────────────────────────────────────

    @http.route(
        '/api/profile',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_profile(self, **_kwargs):
        """Return the logged-in user's profile details."""
        uid, err = self._require_auth()
        if err:
            return err

        try:
            env = request.env
            user = env['res.users'].sudo().browse(uid)
            employee = env['hr.employee'].sudo().search(
                [('user_id', '=', uid)], limit=1
            )

            # Institution — walk the hierarchy
            institution = ''
            if employee:
                if employee.x_sub_jail_id:
                    institution = employee.x_sub_jail_id.name or ''
                elif employee.x_district_jail_id:
                    institution = employee.x_district_jail_id.name or ''
                elif employee.x_central_jail_id:
                    institution = employee.x_central_jail_id.name or ''

            joining_date = ''
            if employee and employee.x_date_of_appointment:
                joining_date = str(employee.x_date_of_appointment)

            mobile = ''
            email = user.email or ''
            if employee:
                mobile = employee.x_mobile_no or ''
                email = employee.work_email or email

            return self._ok({
                'data': {
                    'name':        user.name or '',
                    'username':    user.login or '',
                    'employee_id': (employee.x_employee_code or '') if employee else '',
                    'designation': (employee.x_designation or '') if employee else '',
                    'institution': institution,
                    'mobile':      mobile,
                    'email':       email,
                    'role':        self._get_role(user),
                    'joining_date': joining_date,
                }
            })

        except Exception as exc:
            _logger.exception('GET /api/profile failed for uid=%s: %s', uid, exc)
            return self._err('Failed to load profile.', status=500)

    # ── PUT /api/profile ──────────────────────────────────────────────────────

    @http.route(
        '/api/profile',
        auth='none',
        type='http',
        methods=['PUT'],
        csrf=False,
    )
    def update_profile(self, **_kwargs):
        """Update editable profile fields (mobile, email)."""
        uid, err = self._require_auth()
        if err:
            return err

        body = self._parse_body()
        if body is None:
            return self._err('Invalid JSON body.')

        mobile = (body.get('mobile') or '').strip()
        email  = (body.get('email')  or '').strip()

        if not mobile and not email:
            return self._err('Provide at least one field to update: mobile or email.')

        if mobile and not _MOBILE_RE.match(mobile):
            return self._err('Invalid mobile number. Use digits, spaces, +, or –.')

        if email and not _EMAIL_RE.match(email):
            return self._err('Invalid email address format.')

        try:
            employee = request.env['hr.employee'].sudo().search(
                [('user_id', '=', uid)], limit=1
            )
            if not employee:
                return self._err(
                    'No employee record is linked to your account.', status=404
                )

            vals = {}
            if mobile:
                vals['x_mobile_no'] = mobile
            if email:
                vals['work_email'] = email
                # Also sync to res.users email
                request.env['res.users'].sudo().browse(uid).write({'email': email})

            employee.write(vals)
            return self._ok({'message': 'Profile updated successfully.'})

        except Exception as exc:
            _logger.exception('PUT /api/profile failed for uid=%s: %s', uid, exc)
            return self._err('Failed to update profile.', status=500)

    # ── POST /api/change-password ─────────────────────────────────────────────

    @http.route(
        '/api/change-password',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def change_password(self, **_kwargs):
        """
        Change password for the logged-in user.

        Request : { "current_password": "...", "new_password": "..." }
        Response: { "success": true, "message": "..." }
        """
        uid, err = self._require_auth()
        if err:
            return err

        body = self._parse_body()
        if body is None:
            return self._err('Invalid JSON body.')

        current_pw = body.get('current_password', '')
        new_pw     = body.get('new_password', '')

        if not current_pw:
            return self._err('Current password is required.')
        if not new_pw:
            return self._err('New password is required.')

        # ── Policy validation ─────────────────────────────────────────────────
        if len(new_pw) < _PW_MIN_LEN:
            return self._err(f'Password must be at least {_PW_MIN_LEN} characters.')
        if not _PW_UPPER.search(new_pw):
            return self._err('Password must contain at least one uppercase letter.')
        if not _PW_LOWER.search(new_pw):
            return self._err('Password must contain at least one lowercase letter.')
        if not _PW_DIGIT.search(new_pw):
            return self._err('Password must contain at least one number.')
        if not _PW_SPECIAL.search(new_pw):
            return self._err('Password must contain at least one special character.')
        if current_pw == new_pw:
            return self._err('New password must be different from the current password.')

        try:
            user = request.env['res.users'].sudo().browse(uid)

            # ── Verify current password ───────────────────────────────────────
            # Read the stored password hash directly from the DB and verify
            # using Odoo's own _crypt_context (passlib).  This avoids the
            # fragile _check_credentials / authenticate API which changed
            # signature across Odoo 16 → 19.
            request.env.cr.execute(
                "SELECT COALESCE(password, '') FROM res_users WHERE id = %s AND active = true",
                (uid,),
            )
            row = request.env.cr.fetchone()
            if not row:
                return self._err('User not found.', status=404)

            stored_hash = row[0]
            if not stored_hash:
                return self._err('No password is set for this account.')

            try:
                crypt_ctx = request.env['res.users'].sudo()._crypt_context()
                valid, _ = crypt_ctx.verify_and_update(current_pw, stored_hash)
                if not valid:
                    return self._err('Current password is incorrect.')
            except Exception as exc:
                _logger.exception('Password hash verification failed for uid=%s: %s', uid, exc)
                return self._err('Current password is incorrect.')

            # ── Update password ───────────────────────────────────────────────
            user.write({'password': new_pw})

            # ── Audit log ─────────────────────────────────────────────────────
            try:
                request.env['ir.logging'].sudo().create({
                    'name':    'settings.password_change',
                    'type':    'client',
                    'dbname':  request.db,
                    'level':   'INFO',
                    'message': f'Password changed for user "{user.login}" (uid={uid})',
                    'path':    '/api/change-password',
                    'func':    'change_password',
                    'line':    '0',
                })
            except Exception:
                pass  # Audit failure should not block the response

            _logger.info('Password changed successfully for uid=%s login=%s', uid, user.login)
            return self._ok({'message': 'Password changed successfully.'})

        except Exception as exc:
            _logger.exception('POST /api/change-password failed for uid=%s: %s', uid, exc)
            return self._err('Failed to change password. Please try again.', status=500)
