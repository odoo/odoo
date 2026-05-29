# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

import csv
import io
import json
import logging
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Hard cap on records per page to prevent memory abuse.
_MAX_LIMIT = 100
# Hard cap on rows per import batch
_MAX_IMPORT_ROWS = 500

# ── Field maps ────────────────────────────────────────────────────────────────

# Date fields — require string→Date parsing.
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

# ── CSV configuration ─────────────────────────────────────────────────────────

_CSV_HEADERS = [
    'Employee ID', 'Officer Name', 'Initial', 'Designation', 'Gender', 'Date of Birth',
    'Status', 'Mobile No', 'CUG Mobile No', 'Email',
    'Date of Appointment', 'Date of Promotion', 'Date of Retirement', 'Date Since Present Station',
    'Central Prison', 'District Jail', 'Sub Jail',
    'Panel Year & SL No', 'CPS No', 'GPF No',
    'Religion', 'Community', 'Caste', 'Mother Tongue', 'Education Qualification',
    'Native District', 'Town', 'Taluk', 'Permanent Address',
    'Spouse Employment Details', 'Remarks',
]

# CSV header → API field name (for import).
# Jail columns handled separately (name lookup).
_CSV_IMPORT_MAP = {
    'Employee ID':                'employee_id',
    'Officer Name':               'name',
    'Initial':                    'initial',
    'Designation':                'designation',
    'Gender':                     'gender',
    'Date of Birth':              'dob',
    'Status':                     'status',
    'Mobile No':                  'mobile_no',
    'CUG Mobile No':              'mobile_cug_no',
    'Email':                      'email',
    'Date of Appointment':        'date_of_appointment',
    'Date of Promotion':          'date_of_promotion',
    'Date of Retirement':         'date_of_retirement',
    'Date Since Present Station': 'working_since_present_station',
    'Panel Year & SL No':         'panel_year_sl_no',
    'CPS No':                     'cps_no',
    'GPF No':                     'gpf_no',
    'Religion':                   'religion',
    'Community':                  'community',
    'Caste':                      'caste',
    'Mother Tongue':              'mother_tongue',
    'Education Qualification':    'education_qualification',
    'Native District':            'native_district',
    'Town':                       'town',
    'Taluk':                      'taluk',
    'Permanent Address':          'permanent_address',
    'Spouse Employment Details':  'spouse_employment_details',
    'Remarks':                    'remarks',
}

_VALID_STATUS   = {'active', 'pending', 'transfer', 'inactive'}
_VALID_GENDER   = {'male', 'female', 'other'}
_VALID_RELIGION = {'hinduism', 'islam', 'christianity', 'sikhism', 'buddhism', 'jainism', 'other'}
_VALID_COMMUNITY = {'oc', 'bc', 'bcm', 'mbc', 'dnc', 'sc', 'sca', 'st', 'other'}

# For import: map of API field → valid selection value set (for normalization)
_SELECTION_FIELDS = {
    'gender':    _VALID_GENDER,
    'status':    _VALID_STATUS,
    'religion':  _VALID_RELIGION,
    'community': _VALID_COMMUNITY,
}


class EmployeeAPI(http.Controller):

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _json_response(self, data, status=200):
        """Return a JSON HTTP response with the correct Content-Type header."""
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _require_auth(self):
        """
        Validate that the caller has an active Odoo session.

        Why auth='none' + manual check instead of auth='user'?
        When the Odoo website module is installed, auth='user' routes that
        receive an unauthenticated (or expired-session) request are intercepted
        by the website controller and returned as an HTML login page instead of
        a JSON response.  REST API clients always expect JSON, so we declare
        auth='none' and check the session manually.

        Returns (uid, None) on success or (None, error_response) on failure.
        """
        uid = request.session.uid
        if not uid:
            return None, self._json_response(
                {'success': False, 'message': 'Authentication required'},
                status=401,
            )
        return uid, None

    def _format_employee(self, emp):
        """
        Serialise an hr.employee ORM record to the public API shape.
        Many2one fields are expanded to {id, name} pairs.
        """
        def _date(d): return str(d) if d else ''
        def _str(s):  return s if s else ''

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

    def _emp_to_csv_row(self, emp):
        """Serialise an hr.employee ORM record to a CSV row list."""
        def _d(d): return str(d) if d else ''
        def _s(s): return s if s else ''
        return [
            _s(emp.x_employee_code),
            _s(emp.name),
            _s(emp.x_initial),
            _s(emp.x_designation),
            _s(emp.sex),
            _d(emp.birthday),
            _s(emp.x_status or 'active'),
            _s(emp.x_mobile_no),
            _s(emp.x_cug_mobile),
            _s(emp.work_email),
            _d(emp.x_date_of_appointment),
            _d(emp.x_date_of_promotion),
            _d(emp.x_date_of_retirement),
            _d(emp.x_date_present_station),
            _s(emp.x_central_jail_id.name)  if emp.x_central_jail_id  else '',
            _s(emp.x_district_jail_id.name) if emp.x_district_jail_id else '',
            _s(emp.x_sub_jail_id.name)      if emp.x_sub_jail_id      else '',
            _s(emp.x_panel_year_sl_no),
            _s(emp.x_cps_no),
            _s(emp.x_gpf_no),
            _s(emp.x_religion),
            _s(emp.x_community),
            _s(emp.x_caste),
            _s(emp.x_mother_tongue),
            _s(emp.x_education_qualification),
            _s(emp.x_native_district),
            _s(emp.x_town),
            _s(emp.x_taluk),
            _s(emp.x_permanent_address),
            _s(emp.x_spouse_employment),
            _s(emp.x_remarks),
        ]

    def _parse_write_vals(self, data):
        """
        Convert a JSON/dict of API field names to an Odoo vals dict.
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
                        datetime.strptime(str(raw), '%Y-%m-%d')
                        vals[odoo_key] = str(raw)
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
        PrisonJail  = request.env['prison.jail'].sudo()
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

    def _build_filter_domain(self, kwargs):
        """Build filter domain from query params (shared by list + export)."""
        domain = [('active', '=', True)]

        if kwargs.get('designation'):
            domain.append(('x_designation', 'ilike', kwargs['designation']))

        if kwargs.get('status') and kwargs['status'] != 'all':
            domain.append(('x_status', '=', kwargs['status']))

        if kwargs.get('central_jail_id'):
            try:
                domain.append(('x_central_jail_id', '=', int(kwargs['central_jail_id'])))
            except ValueError:
                pass

        if kwargs.get('native_district'):
            domain.append(('x_native_district', 'ilike', kwargs['native_district']))

        search_domain = self._build_search_or_domain(
            q=kwargs.get('q'),
            name=kwargs.get('name'),
            mobile_cug_no=kwargs.get('mobile_cug_no'),
            employee_id=kwargs.get('employee_id'),
        )
        domain += search_domain
        return domain

    # ── GET /api/employees — paginated list with filters ──────────────────────

    @http.route('/api/employees', auth='none', type='http', methods=['GET'], csrf=False)
    def get_employees(self, **kwargs):
        """
        Fetch paginated employee list.

        Query params
        ------------
        page, limit                     int  pagination (limit max 100)
        q                               str  search across name + employee_id (OR)
        name, mobile_cug_no, employee_id str  individual search fields
        designation                     str  filter by designation (ilike)
        status                          str  filter by x_status exact match
        central_jail_id                 int  filter by central jail ID
        native_district                 str  filter by native district (ilike)
        sort                            str  'name' (default) | 'tenure' | 'designation'
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

            domain = self._build_filter_domain(kwargs)

            sort = kwargs.get('sort', 'name')
            order_map = {
                'name':        'name asc',
                'designation': 'x_designation asc',
                'tenure':      'x_date_present_station asc',
            }
            order = order_map.get(sort, 'name asc')

            Employee    = request.env['hr.employee'].sudo()
            total_count = Employee.search_count(domain)
            records     = Employee.search(domain, offset=offset, limit=limit, order=order)

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

    # ── GET /api/employees/export-csv — CSV export ────────────────────────────

    @http.route('/api/employees/export-csv', auth='user', type='http', methods=['GET'], csrf=False)
    def export_employees(self, **kwargs):
        """
        Export all employees matching the current filters as a CSV file.
        Accepts same filter query params as GET /api/employees (except page/limit).
        """
        try:
            domain = self._build_filter_domain(kwargs)

            sort = kwargs.get('sort', 'name')
            order_map = {
                'name':        'name asc',
                'designation': 'x_designation asc',
                'tenure':      'x_date_present_station asc',
            }
            order  = order_map.get(sort, 'name asc')
            records = request.env['hr.employee'].sudo().search(domain, order=order)

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(_CSV_HEADERS)
            for emp in records:
                writer.writerow(self._emp_to_csv_row(emp))

            filename = f"personnel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return request.make_response(
                output.getvalue(),
                headers=[
                    ('Content-Type', 'text/csv; charset=utf-8'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ],
            )

        except Exception as exc:
            _logger.exception('GET /api/employees/export-csv failed: %s', exc)
            return self._json_response(
                {'success': False, 'message': 'Export failed'},
                status=500,
            )

    # ── GET /api/employees/import-template — blank CSV template ──────────────

    @http.route('/api/employees/import-template', auth='user', type='http', methods=['GET'], csrf=False)
    def import_template(self, **kwargs):
        """Return a blank CSV template with headers + one sample row."""
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(_CSV_HEADERS)
            # Sample row to guide users
            writer.writerow([
                'TN-SUPT-001', 'Sample Officer', 'S.', 'Superintendent', 'male', '1980-01-15',
                'active', '+91 9876543210', '+91 9876543211', 'officer@prison.tn.gov.in',
                '2005-06-01', '2015-03-01', '2040-01-15', '2022-04-01',
                '', '', '',
                '2019/045', 'CPS/2005/001', 'GPF/TN/00001',
                'Hindu', 'OBC', '', 'Tamil', 'B.A.',
                'Chennai', 'Kodambakkam', 'Kodambakkam', '123, Sample Street, Chennai - 600024',
                'Not Applicable', '',
            ])
            return request.make_response(
                output.getvalue(),
                headers=[
                    ('Content-Type', 'text/csv; charset=utf-8'),
                    ('Content-Disposition', 'attachment; filename="personnel_import_template.csv"'),
                ],
            )

        except Exception as exc:
            _logger.exception('GET /api/employees/import-template failed: %s', exc)
            return self._json_response(
                {'success': False, 'message': 'Template generation failed'},
                status=500,
            )

    # ── POST /api/employees/import — bulk CSV import ──────────────────────────

    @http.route('/api/employees/import', auth='user', type='http', methods=['POST'], csrf=False)
    def import_employees(self, **kwargs):
        """
        Bulk-import employees from a CSV file (multipart/form-data, field name: 'file').

        Response
        --------
        {
          "success": true,
          "imported": <int>,
          "skipped":  <int>,
          "errors":   [{"row": <int>, "employee_id": <str>, "name": <str>, "message": <str>}]
        }
        """
        try:
            file_obj = request.httprequest.files.get('file')
            if not file_obj:
                return self._json_response(
                    {'success': False, 'message': 'No file provided. Send a CSV as multipart field "file".'},
                    status=400,
                )

            filename = file_obj.filename or ''
            if not filename.lower().endswith('.csv'):
                return self._json_response(
                    {'success': False, 'message': 'Only CSV files are supported.'},
                    status=400,
                )

            try:
                content = file_obj.read().decode('utf-8-sig')  # Handle Excel BOM
            except UnicodeDecodeError:
                return self._json_response(
                    {'success': False, 'message': 'File encoding error. Please save as UTF-8 CSV.'},
                    status=400,
                )

            reader = csv.DictReader(io.StringIO(content))
            if not reader.fieldnames:
                return self._json_response(
                    {'success': False, 'message': 'Empty or invalid CSV file.'},
                    status=400,
                )

            # Validate required headers are present
            for required_header in ('Employee ID', 'Officer Name'):
                if required_header not in reader.fieldnames:
                    return self._json_response(
                        {'success': False, 'message': f'Missing required column: "{required_header}". Please use the template.'},
                        status=400,
                    )

            rows = list(reader)
            if len(rows) > _MAX_IMPORT_ROWS:
                return self._json_response(
                    {'success': False, 'message': f'Too many rows ({len(rows)}). Maximum {_MAX_IMPORT_ROWS} rows per import.'},
                    status=400,
                )

            Employee   = request.env['hr.employee'].sudo()
            PrisonJail = request.env['prison.jail'].sudo()

            # Pre-load jail name→ID lookup map (case-insensitive)
            jail_name_map = {
                j.name.strip().lower(): j.id
                for j in PrisonJail.search([])
            }

            imported = 0
            skipped  = 0
            errors   = []

            for row_num, row in enumerate(rows, start=2):  # start=2 because row 1 is header
                # Map CSV columns to API field names
                data = {}
                for header, api_key in _CSV_IMPORT_MAP.items():
                    val = row.get(header, '').strip()
                    if val:
                        data[api_key] = val

                # Jail columns: name → ID lookup
                for csv_col, m2o_api_key in [
                    ('Central Prison',  'central_jail_id'),
                    ('District Jail',   'district_jail_id'),
                    ('Sub Jail',        'sub_jail_id'),
                ]:
                    jail_name = row.get(csv_col, '').strip()
                    if jail_name:
                        jail_id = jail_name_map.get(jail_name.lower())
                        if jail_id:
                            data[m2o_api_key] = jail_id

                emp_id   = data.get('employee_id', '').strip()
                emp_name = data.get('name', '').strip()

                # ── Required field validation ──
                if not emp_id:
                    skipped += 1
                    errors.append({'row': row_num, 'employee_id': '—', 'name': emp_name or '—', 'message': 'Employee ID is required'})
                    continue

                if not emp_name:
                    skipped += 1
                    errors.append({'row': row_num, 'employee_id': emp_id, 'name': '—', 'message': 'Officer Name is required'})
                    continue

                # ── Uniqueness check ──
                if Employee.search([('x_employee_code', '=', emp_id)], limit=1):
                    skipped += 1
                    errors.append({'row': row_num, 'employee_id': emp_id, 'name': emp_name, 'message': f'Employee ID "{emp_id}" already exists'})
                    continue

                # ── Normalise Selection field values (case-insensitive) ──
                for api_key, valid_set in _SELECTION_FIELDS.items():
                    if api_key in data:
                        normalised = str(data[api_key]).lower().strip()
                        if normalised in valid_set:
                            data[api_key] = normalised
                        else:
                            data.pop(api_key)  # Skip invalid selection value

                # ── Parse and convert vals ──
                vals, parse_err = self._parse_write_vals(data)
                if parse_err:
                    skipped += 1
                    errors.append({'row': row_num, 'employee_id': emp_id, 'name': emp_name, 'message': parse_err})
                    continue

                # Sanitise status / gender (non-fatal)
                if vals.get('x_status') and vals['x_status'] not in _VALID_STATUS:
                    vals['x_status'] = 'active'
                if vals.get('sex') and vals['sex'] not in _VALID_GENDER:
                    vals.pop('sex', None)

                # Jail hierarchy: if invalid, silently strip jail fields (non-fatal)
                ok, _ = self._validate_jail_hierarchy(vals)
                if not ok:
                    vals.pop('x_central_jail_id',  None)
                    vals.pop('x_district_jail_id', None)
                    vals.pop('x_sub_jail_id',      None)

                # ── Create record ──
                try:
                    Employee.create(vals)
                    imported += 1
                except Exception as create_exc:
                    _logger.error('Import row %d create failed: %s', row_num, create_exc)
                    skipped += 1
                    errors.append({'row': row_num, 'employee_id': emp_id, 'name': emp_name, 'message': 'Database error — failed to create record'})

            return self._json_response({
                'success':  True,
                'imported': imported,
                'skipped':  skipped,
                'errors':   errors,
            })

        except Exception as exc:
            _logger.exception('POST /api/employees/import failed: %s', exc)
            return self._json_response(
                {'success': False, 'message': 'Import failed'},
                status=500,
            )

    # ── GET /api/employees/<employee_id> — single employee detail ─────────────

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

    # ── POST /api/employees — create employee ─────────────────────────────────
    #
    # NOTE: auth='user' (not 'none') — required so request.env.uid is set,
    # which prevents NULL violations in Odoo 19's hr_version parent model.

    @http.route('/api/employees', auth='user', type='http', methods=['POST'], csrf=False)
    def create_employee(self, **kwargs):
        """
        Create a new employee record.

        Request body (JSON)
        -------------------
        name*        str  Full name (required)
        employee_id* str  Unique employee code (required)
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
            if not str(data.get('name', '')).strip():
                return self._json_response(
                    {'success': False, 'message': 'Field "name" is required'},
                    status=400,
                )
            if not str(data.get('employee_id', '')).strip():
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

            vals, err = self._parse_write_vals(data)
            if err:
                return self._json_response({'success': False, 'message': err}, status=400)

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

    # ── PUT /api/employees/<employee_id> — update employee ────────────────────
    #
    # NOTE: auth='user' — see create_employee for rationale.

    @http.route(
        '/api/employees/<string:employee_id>',
        auth='user', type='http', methods=['PUT'], csrf=False,
    )
    def update_employee(self, employee_id, **kwargs):
        """
        Update an existing employee identified by x_employee_code.

        Request body (JSON) — any subset of writable fields.
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
            new_code = str(data.get('employee_id', '')).strip()
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

    # ── DELETE /api/employees/<employee_id> — archive (soft-delete) employee ──
    #
    # auth='none' + _require_auth() so that the website module never intercepts
    # this route and returns an HTML login page instead of JSON.
    #
    # We use active=False (Odoo-standard archive) instead of unlink() because
    # hr.employee records may have related records in other tables (e.g.
    # transfer_approval_request) that hold a FK constraint.  A hard unlink()
    # would raise ForeignKeyViolation.  Archiving hides the record from all
    # active=True searches while preserving referential integrity.

    @http.route(
        '/api/employees/<string:employee_id>',
        auth='none', type='http', methods=['DELETE'], csrf=False,
    )
    def delete_employee(self, employee_id, **kwargs):
        """Archive (soft-delete) an employee record identified by x_employee_code."""
        try:
            uid, err = self._require_auth()
            if err:
                return err

            env = request.env(user=uid)
            emp = env['hr.employee'].sudo().search(
                [('x_employee_code', '=', employee_id), ('active', '=', True)], limit=1,
            )
            if not emp:
                return self._json_response(
                    {'success': False, 'message': 'Employee not found'},
                    status=404,
                )
            emp.write({'active': False})
            return self._json_response(
                {'success': True, 'message': 'Employee deleted successfully'},
            )

        except Exception as exc:
            _logger.exception('DELETE /api/employees/%s failed: %s', employee_id, exc)
            return self._json_response(
                {'success': False, 'message': 'Internal server error'},
                status=500,
            )
