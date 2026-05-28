# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

import json
import logging
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Hard cap on records per page to prevent memory abuse.
_MAX_LIMIT = 100

# Mapping: API response field → Odoo field name (for write operations).
# Date fields are listed separately because they require string→Date parsing.
_DATE_FIELDS = {
    'dob':                           'birthday',
    'date_of_appointment':           'x_date_of_appointment',
    'date_of_promotion':             'x_date_of_promotion',
    'date_of_retirement':            'x_date_of_retirement',
    'working_since_present_station': 'x_date_present_station',
}

# Scalar (non-date, non-relational) writable field map.
_SCALAR_FIELDS = {
    'name':                        'name',
    'initial':                     'x_initial',
    'gender':                      'sex',
    'designation':                 'x_designation',
    'employee_id':                 'x_employee_code',
    'status':                      'x_status',
    'mobile_no':                   'x_mobile_no',
    'mobile_cug_no':               'x_cug_mobile',
    'email':                       'work_email',
    'panel_year_sl_no':            'x_panel_year_sl_no',
    'cps_no':                      'x_cps_no',
    'gpf_no':                      'x_gpf_no',
    'religion':                    'x_religion',
    'community':                   'x_community',
    'caste':                       'x_caste',
    'mother_tongue':               'x_mother_tongue',
    'education_qualification':     'x_education_qualification',
    'native_district':             'x_native_district',
    'town':                        'x_town',
    'taluk':                       'x_taluk',
    'permanent_address':           'x_permanent_address',
    'spouse_employment_details':   'x_spouse_employment',
    'disciplinary_action_pending': 'x_disciplinary_action_pending',
    'remarks':                     'x_remarks',
}

# Many2one field map: API field → Odoo field name.
_M2O_FIELDS = {
    'central_jail_id':  'x_central_jail_id',
    'district_jail_id': 'x_district_jail_id',
    'sub_jail_id':      'x_sub_jail_id',
}


class EmployeeAPI(http.Controller):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _json_response(self, data, status=200):
        """Return a JSON HTTP response with the correct Content-Type header."""
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _format_employee(self, emp):
        """
        Serialise an hr.employee ORM record to the public API shape.
        Many2one fields are expanded to {id, name} pairs.
        """
        def _date(d):
            return str(d) if d else ''

        def _str(s):
            return s if s else ''

        central  = emp.x_central_jail_id
        district = emp.x_district_jail_id
        sub      = emp.x_sub_jail_id

        return {
            'name':                                        _str(emp.name),
            'gender':                                      _str(emp.sex),
            'dob':                                         _date(emp.birthday),
            'initial':                                     _str(emp.x_initial),
            'designation':                                 _str(emp.x_designation),
            'employee_id':                                 _str(emp.x_employee_code),
            'status':                                      _str(emp.x_status or 'active'),
            'mobile_no':                                   _str(emp.x_mobile_no),
            'mobile_cug_no':                               _str(emp.x_cug_mobile),
            'email':                                       _str(emp.work_email),
            'date_of_appointment':                         _date(emp.x_date_of_appointment),
            'date_of_retirement':                          _date(emp.x_date_of_retirement),
            'date_of_promotion':                           _date(emp.x_date_of_promotion),
            'working_since_present_station':               _date(emp.x_date_present_station),
            # Hierarchy Many2one fields
            'central_jail_id':                             central.id or None,
            'central_jail_name':                           _str(central.name),
            'district_jail_id':                            district.id or None,
            'district_jail_name':                          _str(district.name),
            'sub_jail_id':                                 sub.id or None,
            'sub_jail_name':                               _str(sub.name),
            # Legacy text fields (backward compatibility)
            'controlling_central_prison_present_station':  _str(emp.x_central_prison),
            'district_jail_present_station':               _str(emp.x_district_jail),
            'sub_jail_present_station':                    _str(emp.x_sub_jail),
            # Service & personal details
            'panel_year_sl_no':                            _str(emp.x_panel_year_sl_no),
            'cps_no':                                      _str(emp.x_cps_no),
            'gpf_no':                                      _str(emp.x_gpf_no),
            'religion':                                    _str(emp.x_religion),
            'community':                                   _str(emp.x_community),
            'caste':                                       _str(emp.x_caste),
            'mother_tongue':                               _str(emp.x_mother_tongue),
            'education_qualification':                     _str(emp.x_education_qualification),
            'native_district':                             _str(emp.x_native_district),
            'town':                                        _str(emp.x_town),
            'taluk':                                       _str(emp.x_taluk),
            'permanent_address':                           _str(emp.x_permanent_address),
            'spouse_employment_details':                   _str(emp.x_spouse_employment),
            'disciplinary_action_pending':                 bool(emp.x_disciplinary_action_pending),
            'minor_punishment_details':                    _str(emp.x_minor_punishment_details),
            'major_punishment_details':                    _str(emp.x_major_punishment_details),
            'service_history_details':                     _str(emp.x_service_history),
            'training_undergone':                          _str(emp.x_training_undergone),
            'medals':                                      _str(emp.x_medals),
            'rewards':                                     _str(emp.x_rewards),
            'remarks':                                     _str(emp.x_remarks),
        }

    def _parse_write_vals(self, data):
        """
        Convert a JSON request body (API field names) to an Odoo vals dict.
        Returns (vals, error_message). On success error_message is None.
        """
        vals = {}

        # Scalar fields
        for api_key, odoo_key in _SCALAR_FIELDS.items():
            if api_key in data:
                vals[odoo_key] = data[api_key] or False

        # Date fields — accept 'YYYY-MM-DD' strings or empty/null
        for api_key, odoo_key in _DATE_FIELDS.items():
            if api_key in data:
                raw = data[api_key]
                if raw:
                    try:
                        datetime.strptime(raw, '%Y-%m-%d')
                        vals[odoo_key] = raw
                    except ValueError:
                        return None, f"Invalid date format for '{api_key}': expected YYYY-MM-DD"
                else:
                    vals[odoo_key] = False

        # Many2one fields — accept integer IDs or null/0
        for api_key, odoo_key in _M2O_FIELDS.items():
            if api_key in data:
                raw = data[api_key]
                vals[odoo_key] = int(raw) if raw else False

        return vals, None

    def _validate_jail_hierarchy(self, vals):
        """
        Validate the three-tier jail hierarchy in vals.
        Returns (True, None) on success or (False, error_message) on failure.
        """
        PrisonJail = request.env['prison.jail'].sudo()
        central_id  = vals.get('x_central_jail_id')
        district_id = vals.get('x_district_jail_id')
        sub_id      = vals.get('x_sub_jail_id')

        if district_id and central_id:
            district = PrisonJail.browse(district_id)
            if not district.exists():
                return False, 'District Jail not found'
            if district.parent_id.id != central_id:
                return False, (
                    f'District Jail "{district.name}" does not belong to the selected Central Jail'
                )

        if sub_id and district_id:
            sub = PrisonJail.browse(sub_id)
            if not sub.exists():
                return False, 'Sub Jail not found'
            if sub.parent_id.id != district_id:
                return False, (
                    f'Sub Jail "{sub.name}" does not belong to the selected District Jail'
                )

        return True, None

    def _build_search_or_domain(self, q=None, name=None, mobile_cug_no=None, employee_id=None):
        """Build OR domain clauses for search parameters."""
        conditions = []
        # Generic search term (q) hits name and employee_id
        if q:
            conditions.append(('name', 'ilike', q))
            conditions.append(('x_employee_code', 'ilike', q))
        if name:
            conditions.append(('name', 'ilike', name))
        if mobile_cug_no:
            conditions.append(('x_cug_mobile', 'ilike', mobile_cug_no))
        if employee_id:
            conditions.append(('x_employee_code', 'ilike', employee_id))

        if not conditions:
            return []
        if len(conditions) == 1:
            return list(conditions)
        return ['|'] * (len(conditions) - 1) + conditions

    # ------------------------------------------------------------------
    # GET /api/employees — paginated list with filters
    # ------------------------------------------------------------------

    @http.route('/api/employees', auth='none', type='http', methods=['GET'], csrf=False)
    def get_employees(self, **kwargs):
        """
        Fetch paginated employee list.

        Query params
        ------------
        page, limit                 int  pagination (limit max 100)
        q                           str  search across name + employee_id (OR)
        name, mobile_cug_no,        str  individual search fields (OR with each other)
        employee_id
        designation                 str  filter by designation (ilike)
        status                      str  filter by x_status exact match
        central_jail_id             int  filter by central jail ID
        native_district             str  filter by native district (ilike)
        sort                        str  'name' (default) | 'tenure' | 'designation'
        """
        try:
            try:
                page  = max(1, int(kwargs.get('page', 1)))
                limit = max(1, min(_MAX_LIMIT, int(kwargs.get('limit', 20))))
            except (TypeError, ValueError) as exc:
                return self._json_response(
                    {'success': False, 'message': 'Invalid pagination parameter: ' + str(exc)},
                    status=400,
                )
            offset = (page - 1) * limit

            # Base domain — only active Odoo records
            domain = [('active', '=', True)]

            # Filter: designation (ilike match)
            if kwargs.get('designation'):
                domain.append(('x_designation', 'ilike', kwargs['designation']))

            # Filter: status (exact)
            if kwargs.get('status') and kwargs['status'] != 'all':
                domain.append(('x_status', '=', kwargs['status']))

            # Filter: central jail ID
            if kwargs.get('central_jail_id'):
                try:
                    domain.append(('x_central_jail_id', '=', int(kwargs['central_jail_id'])))
                except ValueError:
                    pass

            # Filter: native district (ilike)
            if kwargs.get('native_district'):
                domain.append(('x_native_district', 'ilike', kwargs['native_district']))

            # Search terms (OR logic)
            search_domain = self._build_search_or_domain(
                q=kwargs.get('q'),
                name=kwargs.get('name'),
                mobile_cug_no=kwargs.get('mobile_cug_no'),
                employee_id=kwargs.get('employee_id'),
            )
            domain += search_domain

            # Sort order
            sort = kwargs.get('sort', 'name')
            order_map = {
                'name':        'name asc',
                'designation': 'x_designation asc',
                'tenure':      'x_date_present_station asc',
            }
            order = order_map.get(sort, 'name asc')

            Employee = request.env['hr.employee'].sudo()
            total_count = Employee.search_count(domain)
            records = Employee.search(domain, offset=offset, limit=limit, order=order)

            return self._json_response({
                'success':     True,
                'page':        page,
                'limit':       limit,
                'total_count': total_count,
                'employees':   [self._format_employee(r) for r in records],
            })

        except Exception as exc:
            _logger.exception('GET /api/employees failed: %s', exc)
            return self._json_response(
                {'success': False, 'message': 'Internal server error'},
                status=500,
            )

    # ------------------------------------------------------------------
    # GET /api/employees/<employee_id> — single employee detail
    # ------------------------------------------------------------------

    @http.route(
        '/api/employees/<string:employee_id>',
        auth='none', type='http', methods=['GET'], csrf=False,
    )
    def get_employee(self, employee_id, **kwargs):
        """Fetch a single employee by x_employee_code."""
        try:
            emp = request.env['hr.employee'].sudo().search(
                [('x_employee_code', '=', employee_id), ('active', '=', True)],
                limit=1,
            )
            if not emp:
                return self._json_response(
                    {'success': False, 'message': 'Employee not found'},
                    status=404,
                )
            return self._json_response({'success': True, 'employee': self._format_employee(emp)})

        except Exception as exc:
            _logger.exception('GET /api/employees/%s failed: %s', employee_id, exc)
            return self._json_response(
                {'success': False, 'message': 'Internal server error'},
                status=500,
            )

    # ------------------------------------------------------------------
    # POST /api/employees — create employee
    # ------------------------------------------------------------------

    @http.route('/api/employees', auth='none', type='http', methods=['POST'], csrf=False)
    def create_employee(self, **kwargs):
        """
        Create a new employee record.

        Request body (JSON)
        -------------------
        name*             str  Full name (required)
        employee_id*      str  Unique employee code (required)
        + any fields listed in _SCALAR_FIELDS, _DATE_FIELDS, _M2O_FIELDS
        """
        try:
            raw = request.httprequest.get_data(as_text=True)
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return self._json_response(
                    {'success': False, 'message': 'Invalid JSON body'},
                    status=400,
                )

            # Required field validation
            if not data.get('name', '').strip():
                return self._json_response(
                    {'success': False, 'message': 'Field "name" is required'},
                    status=400,
                )
            if not data.get('employee_id', '').strip():
                return self._json_response(
                    {'success': False, 'message': 'Field "employee_id" is required'},
                    status=400,
                )

            # Uniqueness check
            existing = request.env['hr.employee'].sudo().search(
                [('x_employee_code', '=', data['employee_id'].strip())], limit=1,
            )
            if existing:
                return self._json_response(
                    {'success': False, 'message': f'Employee ID "{data["employee_id"]}" already exists'},
                    status=409,
                )

            # Parse and validate vals
            vals, err = self._parse_write_vals(data)
            if err:
                return self._json_response({'success': False, 'message': err}, status=400)

            # Validate jail hierarchy
            ok, err = self._validate_jail_hierarchy(vals)
            if not ok:
                return self._json_response({'success': False, 'message': err}, status=400)

            emp = request.env['hr.employee'].sudo().create(vals)
            return self._json_response(
                {'success': True, 'message': 'Employee created', 'employee': self._format_employee(emp)},
                status=201,
            )

        except Exception as exc:
            _logger.exception('POST /api/employees failed: %s', exc)
            return self._json_response(
                {'success': False, 'message': 'Internal server error'},
                status=500,
            )

    # ------------------------------------------------------------------
    # PUT /api/employees/<employee_id> — update employee
    # ------------------------------------------------------------------

    @http.route(
        '/api/employees/<string:employee_id>',
        auth='none', type='http', methods=['PUT'], csrf=False,
    )
    def update_employee(self, employee_id, **kwargs):
        """
        Update an existing employee identified by x_employee_code.

        Request body (JSON) — any subset of writable fields.
        If 'employee_id' is included and differs from the path param,
        it will be used as the new employee code (uniqueness is checked).
        """
        try:
            emp = request.env['hr.employee'].sudo().search(
                [('x_employee_code', '=', employee_id)], limit=1,
            )
            if not emp:
                return self._json_response(
                    {'success': False, 'message': 'Employee not found'},
                    status=404,
                )

            raw = request.httprequest.get_data(as_text=True)
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return self._json_response(
                    {'success': False, 'message': 'Invalid JSON body'},
                    status=400,
                )

            # If employee_id is being changed, check uniqueness
            new_code = data.get('employee_id', '').strip()
            if new_code and new_code != employee_id:
                conflict = request.env['hr.employee'].sudo().search(
                    [('x_employee_code', '=', new_code), ('id', '!=', emp.id)], limit=1,
                )
                if conflict:
                    return self._json_response(
                        {'success': False, 'message': f'Employee ID "{new_code}" already in use'},
                        status=409,
                    )

            vals, err = self._parse_write_vals(data)
            if err:
                return self._json_response({'success': False, 'message': err}, status=400)

            ok, err = self._validate_jail_hierarchy(vals)
            if not ok:
                return self._json_response({'success': False, 'message': err}, status=400)

            emp.write(vals)
            return self._json_response(
                {'success': True, 'message': 'Employee updated', 'employee': self._format_employee(emp)},
            )

        except Exception as exc:
            _logger.exception('PUT /api/employees/%s failed: %s', employee_id, exc)
            return self._json_response(
                {'success': False, 'message': 'Internal server error'},
                status=500,
            )

    # ------------------------------------------------------------------
    # DELETE /api/employees/<employee_id> — delete employee
    # ------------------------------------------------------------------

    @http.route(
        '/api/employees/<string:employee_id>',
        auth='none', type='http', methods=['DELETE'], csrf=False,
    )
    def delete_employee(self, employee_id, **kwargs):
        """Delete an employee record identified by x_employee_code."""
        try:
            emp = request.env['hr.employee'].sudo().search(
                [('x_employee_code', '=', employee_id)], limit=1,
            )
            if not emp:
                return self._json_response(
                    {'success': False, 'message': 'Employee not found'},
                    status=404,
                )
            emp.unlink()
            return self._json_response(
                {'success': True, 'message': 'Employee deleted successfully'},
            )

        except Exception as exc:
            _logger.exception('DELETE /api/employees/%s failed: %s', employee_id, exc)
            return self._json_response(
                {'success': False, 'message': 'Internal server error'},
                status=500,
            )
