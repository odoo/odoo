# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

"""
Users REST API
==============

Admin-only endpoints for listing and viewing system users (res.users).

Auth: all endpoints require a valid Odoo admin session (auth='none' + _require_auth + _is_admin).

Endpoints
---------
GET  /api/users           — Paginated list with search / filter
GET  /api/users/<int:id>  — Single user detail
"""

import json
import logging

from odoo import http
from odoo.http import request

_logger    = logging.getLogger(__name__)
_MAX_LIMIT = 100


class UsersApiController(http.Controller):

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _json(self, data, status=200):
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _ok(self, **data):
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

    def _is_admin_user(self, user):
        try:
            return (
                user.has_group('base.group_system') or
                user.has_group('base.group_erp_manager')
            )
        except Exception:
            return False

    def _get_user_type(self, user):
        try:
            if user.has_group('base.group_system'):
                return 'Super Admin'
            if user.has_group('base.group_erp_manager'):
                return 'Admin'
        except Exception:
            pass
        return 'User'

    def _matches_user_type(self, user, user_type):
        """Check if a user matches the requested type using has_group (reliable for superusers)."""
        utype = self._get_user_type(user)
        if user_type == 'super_admin':
            return utype == 'Super Admin'
        if user_type == 'admin':
            return utype == 'Admin'
        if user_type == 'user':
            return utype == 'User'
        return True

    def _format_user(self, user):
        """Serialize res.users record to public API shape."""
        emp = user.employee_ids[:1] if user.employee_ids else None

        # Institution: walk Sub > District > Central; then legacy text fields
        institution      = ''
        institution_type = ''
        central_jail_id   = None
        central_jail_name = ''
        if emp:
            if emp.x_sub_jail_id:
                institution      = emp.x_sub_jail_id.name or ''
                institution_type = 'sub_jail'
            elif emp.x_district_jail_id:
                institution      = emp.x_district_jail_id.name or ''
                institution_type = 'district_jail'
            elif emp.x_central_jail_id:
                institution      = emp.x_central_jail_id.name or ''
                institution_type = 'central_jail'
            elif getattr(emp, 'x_sub_jail', None):
                institution      = emp.x_sub_jail or ''
                institution_type = 'sub_jail'
            elif getattr(emp, 'x_district_jail', None):
                institution      = emp.x_district_jail or ''
                institution_type = 'district_jail'
            elif getattr(emp, 'x_central_prison', None):
                institution      = emp.x_central_prison or ''
                institution_type = 'central_jail'

            if emp.x_central_jail_id:
                central_jail_id   = emp.x_central_jail_id.id
                central_jail_name = emp.x_central_jail_id.name or ''

        email  = ''
        mobile = ''
        if emp:
            email  = emp.work_email or user.email or ''
            mobile = getattr(emp, 'x_mobile_no', '') or ''
        else:
            email = user.email or ''

        return {
            'id':              user.id,
            'name':            user.name or '',
            'login':           user.login or '',
            'email':           email,
            'mobile':          mobile,
            'user_type':       self._get_user_type(user),
            'active':          user.active,
            'status':          'active' if user.active else 'inactive',
            'last_login':      str(user.login_date) if user.login_date else '',
            'create_date':     str(user.create_date) if user.create_date else '',
            # Linked employee
            'employee_db_id':  emp.id if emp else None,
            'employee_id':     (emp.x_employee_code or '') if emp else '',
            'designation':     (emp.x_designation or '') if emp else '',
            'institution':     institution,
            'institution_type': institution_type,
            'central_jail_id':   central_jail_id,
            'central_jail_name': central_jail_name,
        }

    # ── GET /api/users ────────────────────────────────────────────────────────

    @http.route(
        '/api/users',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def list_users(self, **kwargs):
        """Return paginated list of internal system users (admin-only)."""
        uid, err = self._require_auth()
        if err:
            return err

        current_user = request.env['res.users'].sudo().browse(uid)
        if not self._is_admin_user(current_user):
            return self._err('Access denied. Admin privileges required.', status=403)

        try:
            page   = max(1, int(kwargs.get('page', 1)))
            limit  = max(1, min(_MAX_LIMIT, int(kwargs.get('limit', 20))))
            offset = (page - 1) * limit

            q               = (kwargs.get('q')               or '').strip()
            user_type       = (kwargs.get('user_type')       or '').strip().lower()
            status          = (kwargs.get('status')          or 'active').strip().lower()
            central_jail_id = kwargs.get('central_jail_id')

            # Base domain: internal (non-portal) users only
            domain = [('share', '=', False)]

            # Status filter — explicit active condition; active_test=False lets us reach inactive users
            if status == 'inactive':
                domain.append(('active', '=', False))
            elif status == 'active':
                domain.append(('active', '=', True))
            # status == 'all' → no active condition, active_test=False returns all

            # Full-text search: name | login | employee code
            if q:
                domain += [
                    '|', ('name', 'ilike', q),
                    '|', ('login', 'ilike', q),
                         ('employee_ids.x_employee_code', 'ilike', q),
                ]

            # Prison filter (via linked employee's central jail)
            if central_jail_id:
                try:
                    domain.append(
                        ('employee_ids.x_central_jail_id', '=', int(central_jail_id))
                    )
                except (ValueError, TypeError):
                    pass

            # Fetch all records matching domain (active_test=False reaches inactive users)
            Users   = request.env['res.users'].sudo().with_context(active_test=False)
            records = Users.search(domain, order='name asc')

            # Post-filter by user_type using has_group — more reliable than groups_id domain
            # because Odoo's superuser (uid=1) bypasses group checks but has_group handles it.
            if user_type:
                records = records.filtered(
                    lambda u: self._matches_user_type(u, user_type)
                )

            total_count = len(records)
            paged       = records[offset: offset + limit]

            return self._json({
                'success':     True,
                'page':        page,
                'limit':       limit,
                'total_count': total_count,
                'users':       [self._format_user(u) for u in paged],
            })

        except Exception as exc:
            _logger.exception('GET /api/users failed: %s', exc)
            return self._err('Failed to load users.', status=500)

    # ── GET /api/users/<int:user_id> ──────────────────────────────────────────

    @http.route(
        '/api/users/<int:user_id>',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_user(self, user_id, **kwargs):
        """Return full detail for a single user (admin-only)."""
        uid, err = self._require_auth()
        if err:
            return err

        current_user = request.env['res.users'].sudo().browse(uid)
        if not self._is_admin_user(current_user):
            return self._err('Access denied. Admin privileges required.', status=403)

        try:
            user = request.env['res.users'].sudo().with_context(active_test=False).browse(user_id)
            if not user.exists() or user.share:
                return self._err('User not found.', status=404)

            return self._json({'success': True, 'user': self._format_user(user)})

        except Exception as exc:
            _logger.exception('GET /api/users/%s failed: %s', user_id, exc)
            return self._err('Failed to load user.', status=500)
