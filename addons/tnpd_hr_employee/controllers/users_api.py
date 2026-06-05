# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

"""
Users REST API
==============

Admin-only endpoints for listing and managing system users (res.users).

Auth: all endpoints require a valid Odoo admin session (auth='none' + _require_auth + _is_admin).

Endpoints
---------
GET    /api/users                      — Paginated list with search / filter
GET    /api/users/<int:id>             — Single user detail
PUT    /api/users/<int:id>             — Update name / email / mobile / user_type
DELETE /api/users/<int:id>             — Archive user (soft-delete, active=False)
POST   /api/users/<int:id>/reactivate  — Restore archived user (active=True)
"""

import json
import logging
import re

from odoo import http
from odoo.http import request

_EMAIL_RE  = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_MOBILE_RE = re.compile(r'^[+]?[\d\s\-()×]{7,20}$')

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

    # ── PUT /api/users/<int:user_id> ──────────────────────────────────────────

    @http.route(
        '/api/users/<int:user_id>',
        auth='none',
        type='http',
        methods=['PUT'],
        csrf=False,
    )
    def update_user(self, user_id, **kwargs):
        """Update editable fields for a user: name, email, mobile, user_type."""
        uid, err = self._require_auth()
        if err:
            return err

        current_user = request.env['res.users'].sudo().browse(uid)
        if not self._is_admin_user(current_user):
            return self._err('Access denied. Admin privileges required.', status=403)

        try:
            body = json.loads(request.httprequest.get_data(as_text=True) or '{}')
        except Exception:
            return self._err('Invalid JSON body.')

        try:
            env  = request.env
            user = env['res.users'].sudo().with_context(active_test=False).browse(user_id)
            if not user.exists() or user.share:
                return self._err('User not found.', status=404)

            # Super Admin can only be edited by another Super Admin
            target_type = self._get_user_type(user)
            is_current_super = current_user.has_group('base.group_system')
            if target_type == 'Super Admin' and not is_current_super:
                return self._err('Only a Super Admin can edit a Super Admin account.', status=403)

            # ── Field validation ──────────────────────────────────────────────
            name      = (body.get('name')      or '').strip()
            email     = (body.get('email')     or '').strip()
            mobile    = (body.get('mobile')    or '').strip()
            user_type = (body.get('user_type') or '').strip().lower()

            if not name:
                return self._err('Name is required.')
            if email and not _EMAIL_RE.match(email):
                return self._err('Invalid email address format.')
            if mobile and not _MOBILE_RE.match(mobile):
                return self._err('Invalid mobile number format.')
            if user_type and user_type not in ('admin', 'user'):
                return self._err('user_type must be "admin" or "user".')

            # ── Apply updates ─────────────────────────────────────────────────
            user_vals = {'name': name}
            if email:
                user_vals['email'] = email
            user.write(user_vals)

            # Sync to linked employee if present
            emp = user.employee_ids[:1] if user.employee_ids else None
            if emp:
                emp_vals = {}
                if email:
                    emp_vals['work_email'] = email
                if mobile:
                    emp_vals['x_mobile_no'] = mobile
                if emp_vals:
                    emp.write(emp_vals)

            # ── User type change ──────────────────────────────────────────────
            if user_type and target_type != 'Super Admin':
                group_erp = env.ref('base.group_erp_manager', raise_if_not_found=False)
                if group_erp:
                    if user_type == 'admin':
                        user.write({'groups_id': [(4, group_erp.id)]})
                    elif user_type == 'user':
                        user.write({'groups_id': [(3, group_erp.id)]})

            return self._json({'success': True, 'message': 'User updated successfully.', 'user': self._format_user(user)})

        except Exception as exc:
            _logger.exception('PUT /api/users/%s failed: %s', user_id, exc)
            return self._err('Failed to update user.', status=500)

    # ── DELETE /api/users/<int:user_id> ───────────────────────────────────────

    @http.route(
        '/api/users/<int:user_id>',
        auth='none',
        type='http',
        methods=['DELETE'],
        csrf=False,
    )
    def delete_user(self, user_id, **kwargs):
        """Archive (soft-delete) a user — sets active=False."""
        uid, err = self._require_auth()
        if err:
            return err

        current_user = request.env['res.users'].sudo().browse(uid)
        if not self._is_admin_user(current_user):
            return self._err('Access denied. Admin privileges required.', status=403)

        # Prevent self-deletion
        if user_id == uid:
            return self._err('You cannot delete your own account.', status=400)

        try:
            user = request.env['res.users'].sudo().with_context(active_test=False).browse(user_id)
            if not user.exists() or user.share:
                return self._err('User not found.', status=404)

            # Super Admin can only be deleted by another Super Admin
            target_type = self._get_user_type(user)
            is_current_super = current_user.has_group('base.group_system')
            if target_type == 'Super Admin' and not is_current_super:
                return self._err('Only a Super Admin can delete a Super Admin account.', status=403)

            user.write({'active': False})
            return self._json({'success': True, 'message': f'User "{user.name}" has been deactivated.'})

        except Exception as exc:
            _logger.exception('DELETE /api/users/%s failed: %s', user_id, exc)
            return self._err('Failed to delete user.', status=500)

    # ── POST /api/users/<int:user_id>/reactivate ──────────────────────────────

    @http.route(
        '/api/users/<int:user_id>/reactivate',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
    )
    def reactivate_user(self, user_id, **kwargs):
        """Restore an archived user — sets active=True."""
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

            if user.active:
                return self._err('User is already active.', status=400)

            user.write({'active': True})
            return self._json({'success': True, 'message': f'User "{user.name}" has been reactivated.'})

        except Exception as exc:
            _logger.exception('POST /api/users/%s/reactivate failed: %s', user_id, exc)
            return self._err('Failed to reactivate user.', status=500)
