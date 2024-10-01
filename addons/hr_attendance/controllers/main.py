# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.service.common import exp_version
from odoo import http, _
from odoo.http import request
from odoo.osv import expression
from odoo.tools import float_round, py_to_js_locale, SQL
from odoo.tools.image import image_data_uri

import datetime

class HrAttendance(http.Controller):
    @staticmethod
    def _get_company(token):
        company = request.env['res.company'].sudo().search([('attendance_kiosk_key', '=', token)])
        return company

    @staticmethod
    def _get_user_attendance_data(employee):
        response = {}
        if employee:
            response = {
                'id': employee.id,
                'hours_today': float_round(employee.hours_today, precision_digits=2),
                'hours_previously_today': float_round(employee.hours_previously_today, precision_digits=2),
                'last_attendance_worked_hours': float_round(employee.last_attendance_worked_hours, precision_digits=2),
                'last_check_in': employee.last_check_in,
                'attendance_state': employee.attendance_state,
                'display_systray': employee.company_id.attendance_from_systray,
            }
        return response

    @staticmethod
    def _get_employee_info_response(employee):
        response = {}
        if employee:
            response = {
                **HrAttendance._get_user_attendance_data(employee),
                'employee_name': employee.name,
                'employee_avatar': employee.image_256 and image_data_uri(employee.image_256),
                'total_overtime': float_round(employee.total_overtime, precision_digits=2),
                'kiosk_delay': employee.company_id.attendance_kiosk_delay * 1000,
                'attendance': {'check_in': employee.last_attendance_id.check_in,
                               'check_out': employee.last_attendance_id.check_out},
                'overtime_today': request.env['hr.attendance.overtime'].sudo().search([
                    ('employee_id', '=', employee.id), ('date', '=', datetime.date.today()),
                    ('adjustment', '=', False)]).duration or 0,
                'use_pin': employee.company_id.attendance_kiosk_use_pin,
                'display_overtime': employee.company_id.hr_attendance_display_overtime
            }
        return response

    @staticmethod
    def _get_geoip_response(mode, latitude=False, longitude=False):
        return {
            'city': request.geoip.city.name or _('Unknown'),
            'country_name': request.geoip.country.name or request.geoip.continent.name or _('Unknown'),
            'latitude': latitude or request.geoip.location.latitude or False,
            'longitude': longitude or request.geoip.location.longitude or False,
            'ip_address': request.geoip.ip,
            'browser': request.httprequest.user_agent.browser,
            'mode': mode
        }

    @http.route('/hr_attendance/kiosk_mode_menu/<int:company_id>', auth='user', type='http')
    def kiosk_menu_item_action(self, company_id):
        if request.env.user.has_group("hr_attendance.group_hr_attendance_manager"):
            # Auto log out will prevent users from forgetting to log out of their session
            # before leaving the kiosk mode open to the public. This is a prevention security
            # measure.
            if self.has_password():
                request.session.logout(keep_db=True)
            return request.redirect(request.env['res.company'].browse(company_id).attendance_kiosk_url)
        else:
            return request.not_found()

    @http.route('/hr_attendance/kiosk_keepalive', auth='user', type='json')
    def kiosk_keepalive(self):
        request.session.touch()
        return {}

    @http.route(["/hr_attendance/<token>"], type='http', auth='public', website=True, sitemap=True)
    def open_kiosk_mode(self, token, from_trial_mode=False):
        company = self._get_company(token)
        if not company:
            return request.not_found()
        else:
            department_list = [{'id': dep["id"],
                                 'name': dep["name"],
                                 'count': dep["total_employee"]
                                 } for dep in request.env['hr.department'].sudo().search_read(domain=[('company_id', '=', company.id)],
                                                                                              fields=["id",
                                                                                                      "name",
                                                                                                      "total_employee"])]
            has_password = self.has_password()
            if not from_trial_mode and has_password:
                request.session.logout(keep_db=True)
            if (from_trial_mode or not has_password):
                kiosk_mode = "settings"
            else:
                kiosk_mode = company.attendance_kiosk_mode
            version_info = exp_version()
            return request.render(
                'hr_attendance.public_kiosk_mode',
                {
                    'kiosk_backend_info': {
                        'token': token,
                        'company_id': company.id,
                        'company_name': company.name,
                        'departments': department_list,
                        'kiosk_mode': kiosk_mode,
                        'from_trial_mode': from_trial_mode,
                        'barcode_source': company.attendance_barcode_source,
                        'lang': py_to_js_locale(company.partner_id.lang),
                        'server_version_info': version_info.get('server_version_info'),
                    },
                }
            )

    @http.route('/hr_attendance/attendance_employee_data', type="json", auth="public")
    def employee_attendance_data(self, token, employee_id):
        company = self._get_company(token)
        if company:
            employee = request.env['hr.employee'].sudo().browse(employee_id)
            if employee.company_id == company:
                return self._get_employee_info_response(employee)
        return {}

    @http.route('/hr_attendance/attendance_barcode_scanned', type="json", auth="public")
    def scan_barcode(self, token, barcode):
        company = self._get_company(token)
        if company:
            employee = request.env['hr.employee'].sudo().search([('barcode', '=', barcode), ('company_id', '=', company.id)], limit=1)
            if employee:
                employee._attendance_action_change(self._get_geoip_response('kiosk'))
                return self._get_employee_info_response(employee)
        return {}

    @http.route('/hr_attendance/manual_selection', type="json", auth="public")
    def manual_selection(self, token, employee_id, pin_code):
        company = self._get_company(token)
        if company:
            employee = request.env['hr.employee'].sudo().browse(employee_id)
            if employee.company_id == company and ((not company.attendance_kiosk_use_pin) or (employee.pin == pin_code)):
                employee.sudo()._attendance_action_change(self._get_geoip_response('kiosk'))
                return self._get_employee_info_response(employee)
        return {}

    @http.route('/hr_attendance/employees_infos', type="json", auth="public")
    def employees_infos(self, token, limit, offset, domain):
        company = self._get_company(token)
        if company:
            domain = expression.AND([domain, [('company_id', '=', company.id)]])
            employees = request.env['hr.employee'].sudo().search_fetch(domain, ['id', 'display_name', 'job_id'],
                limit=limit, offset=offset, order="name, id")
            employees_data = [{
                'id': employee.id,
                'display_name': employee.display_name,
                'job_id': employee.job_id.name,
                'avatar': image_data_uri(employee.avatar_128)
            } for employee in employees]
            return {'records': employees_data, 'length': request.env['hr.employee'].sudo().search_count(domain)}
        return []

    @http.route('/hr_attendance/systray_check_in_out', type="json", auth="user")
    def systray_attendance(self, latitude=False, longitude=False):
        employee = request.env.user.employee_id
        geo_ip_response = self._get_geoip_response(mode='systray',
                                                  latitude=latitude,
                                                  longitude=longitude)
        employee._attendance_action_change(geo_ip_response)
        return self._get_employee_info_response(employee)

    @http.route('/hr_attendance/attendance_user_data', type="json", auth="user")
    def user_attendance_data(self):
        employee = request.env.user.employee_id
        return self._get_user_attendance_data(employee)

    def has_password(self):
        # With this method we try to know whether it's the user is on trial mode or not.
        # We assume that in trial, people have not configured their password yet and their password should be empty.
        request.env.cr.execute(
            SQL('''
                SELECT COUNT(password)
                  FROM res_users
                 WHERE id=%(user_id)s
                   AND password IS NOT NULL
                 LIMIT 1
                ''', user_id=request.env.user.id))
        return bool(request.env.cr.fetchone()[0])

    @http.route('/hr_attendance/is_fresh_db', type="json", auth="public")
    def is_fresh_db(self, token):
        company = self._get_company(token)
        if company:
            users = request.env['res.users'].sudo().search([])
            return len(users) == 1 and not users[0].employee_id.barcode
        return False

    @http.route('/hr_attendance/set_user_barcode', type="json", auth="public")
    def set_user_barcode(self, token, barcode):
        company = self._get_company(token)
        if company and self.is_fresh_db(token):
            request.env.user.employee_id.barcode = barcode
            return True
        return False

    @http.route('/hr_attendance/set_settings', type="json", auth="public")
    def set_attendance_settings(self, token, mode):
        company = self._get_company(token)
        if company:
            request.env.user.company_id.attendance_kiosk_mode = mode
