# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Odoo internal fields fetched from hr.employee for each API response.
# Mapping: API response key -> Odoo field name (resolved in _format_employee).
_FETCH_FIELDS = [
    'name',
    'sex',
    'birthday',
    'x_designation',
    'x_employee_code',
    'x_cps_no',
    'x_gpf_no',
    'x_cug_mobile',
    'x_date_of_appointment',
    'x_date_of_retirement',
    'x_permanent_address',
    'x_taluk',
    'x_town',
    'x_panel_year_sl_no',
    'x_native_district',
    'x_religion',
    'x_community',
    'x_caste',
    'x_mother_tongue',
    'x_education_qualification',
    'x_date_present_station',
    'x_central_prison',
    'x_sub_jail',
    'x_district_jail',
    'x_disciplinary_action_pending',
    'x_minor_punishment_details',
    'x_service_history',
    'x_medals',
    'x_rewards',
    'x_spouse_employment',
    'x_remarks',
    'x_initial',
    'x_mobile_no',
    'x_major_punishment_details',
    'x_training_undergone',
    'x_date_of_promotion',
]

# Hard cap on records per page to prevent memory abuse.
_MAX_LIMIT = 100


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

    def _format_employee(self, record):
        """
        Translate a search_read dict (internal field names) into the
        public API shape (API field names).  Date/boolean fields are
        normalised so they never arrive as Odoo False values.
        """
        def _date(val):
            return str(val) if val else ''

        def _str(val):
            return val if val else ''

        return {
            'name':                                         _str(record.get('name')),
            'gender':                                       _str(record.get('sex')),
            'designation':                                  _str(record.get('x_designation')),
            'employee_id':                                  _str(record.get('x_employee_code')),
            'cps_no':                                       _str(record.get('x_cps_no')),
            'gpf_no':                                       _str(record.get('x_gpf_no')),
            'dob':                                          _date(record.get('birthday')),
            'mobile_cug_no':                                _str(record.get('x_cug_mobile')),
            'date_of_appointment':                          _date(record.get('x_date_of_appointment')),
            'date_of_retirement':                           _date(record.get('x_date_of_retirement')),
            'permanent_address':                            _str(record.get('x_permanent_address')),
            'taluk':                                        _str(record.get('x_taluk')),
            'town':                                         _str(record.get('x_town')),
            'panel_year_sl_no':                             _str(record.get('x_panel_year_sl_no')),
            'native_district':                              _str(record.get('x_native_district')),
            'religion':                                     _str(record.get('x_religion')),
            'community':                                    _str(record.get('x_community')),
            'caste':                                        _str(record.get('x_caste')),
            'mother_tongue':                                _str(record.get('x_mother_tongue')),
            'education_qualification':                      _str(record.get('x_education_qualification')),
            'working_since_present_station':                _date(record.get('x_date_present_station')),
            'controlling_central_prison_present_station':   _str(record.get('x_central_prison')),
            'sub_jail_present_station':                     _str(record.get('x_sub_jail')),
            'district_jail_present_station':                _str(record.get('x_district_jail')),
            'disciplinary_action_pending':                  bool(record.get('x_disciplinary_action_pending')),
            'minor_punishment_details':                     _str(record.get('x_minor_punishment_details')),
            'service_history_details':                      _str(record.get('x_service_history')),
            'medals':                                       _str(record.get('x_medals')),
            'rewards':                                      _str(record.get('x_rewards')),
            'spouse_employment_details':                    _str(record.get('x_spouse_employment')),
            'remarks':                                      _str(record.get('x_remarks')),
            'initial':                                      _str(record.get('x_initial')),
            'mobile_no':                                    _str(record.get('x_mobile_no')),
            'major_punishment_details':                     _str(record.get('x_major_punishment_details')),
            'training_undergone':                           _str(record.get('x_training_undergone')),
            'date_of_promotion':                            _date(record.get('x_date_of_promotion')),
        }

    def _build_search_or_domain(self, kwargs):
        """
        Build OR domain clauses for the three search parameters.
        Returns an empty list when no search params are provided.
        """
        conditions = []
        if kwargs.get('name'):
            conditions.append(('name', 'ilike', kwargs['name']))
        if kwargs.get('mobile_cug_no'):
            conditions.append(('x_cug_mobile', 'ilike', kwargs['mobile_cug_no']))
        if kwargs.get('employee_id'):
            conditions.append(('x_employee_code', 'ilike', kwargs['employee_id']))

        if not conditions:
            return []
        if len(conditions) == 1:
            return list(conditions)

        # For N conditions joined by OR, Odoo needs N-1 '|' prefix operators.
        return ['|'] * (len(conditions) - 1) + conditions

    # ------------------------------------------------------------------
    # API 1 – Fetch Employees
    # GET /api/employees
    # ------------------------------------------------------------------

    @http.route(
        '/api/employees',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_employees(self, **kwargs):
        """
        Fetch paginated employee list with optional filters and search.

        Query params
        ------------
        page                            int  (default 1)
        limit                           int  (default 20, max 100)
        district_jail_present_station   str  filter
        sub_jail_present_station        str  filter
        native_district                 str  filter
        name                            str  search (OR'd with the others)
        mobile_cug_no                   str  search
        employee_id                     str  search
        """
        try:
            # --- Pagination -------------------------------------------------
            try:
                page = max(1, int(kwargs.get('page', 1)))
                limit = max(1, min(_MAX_LIMIT, int(kwargs.get('limit', 20))))
            except (TypeError, ValueError) as exc:
                return self._json_response(
                    {'success': False, 'message': 'Invalid pagination parameter: ' + str(exc)},
                    status=400,
                )
            offset = (page - 1) * limit

            # --- Base domain (only active employees) ------------------------
            domain = [('active', '=', True)]

            # --- Filter domain (AND logic) -----------------------------------
            if kwargs.get('district_jail_present_station'):
                domain.append(('x_district_jail', 'ilike', kwargs['district_jail_present_station']))
            if kwargs.get('sub_jail_present_station'):
                domain.append(('x_sub_jail', 'ilike', kwargs['sub_jail_present_station']))
            if kwargs.get('native_district'):
                domain.append(('x_native_district', 'ilike', kwargs['native_district']))

            # --- Search domain (OR logic across search fields) ---------------
            search_domain = self._build_search_or_domain(kwargs)
            domain += search_domain

            # --- Query -------------------------------------------------------
            Employee = request.env['hr.employee'].sudo()
            total_count = Employee.search_count(domain)
            records = Employee.search_read(
                domain=domain,
                fields=_FETCH_FIELDS,
                offset=offset,
                limit=limit,
                order='name asc',
            )

            return self._json_response({
                'success': True,
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'employees': [self._format_employee(r) for r in records],
            })

        except Exception as exc:
            _logger.exception('GET /api/employees failed: %s', exc)
            return self._json_response(
                {'success': False, 'message': 'Internal server error'},
                status=500,
            )

    # ------------------------------------------------------------------
    # API 2 – Delete Employee
    # DELETE /api/employees/<employee_id>
    # ------------------------------------------------------------------

    @http.route(
        '/api/employees/<string:employee_id>',
        auth='none',
        type='http',
        methods=['DELETE'],
        csrf=False,
    )
    def delete_employee(self, employee_id, **kwargs):
        """
        Delete an employee record identified by the x_employee_code field.

        Path param
        ----------
        employee_id   str  value of the x_employee_code field (e.g. EMP001)
        """
        try:
            employee = request.env['hr.employee'].sudo().search(
                [('x_employee_code', '=', employee_id)],
                limit=1,
            )

            if not employee:
                return self._json_response(
                    {'success': False, 'message': 'Employee not found'},
                    status=404,
                )

            employee.unlink()

            return self._json_response(
                {'success': True, 'message': 'Employee deleted successfully'},
            )

        except Exception as exc:
            _logger.exception('DELETE /api/employees/%s failed: %s', employee_id, exc)
            return self._json_response(
                {'success': False, 'message': 'Internal server error'},
                status=500,
            )
