# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.tools import float_round
import datetime

class HrAttendance(http.Controller):
    @staticmethod
    def _get_company(token):
        company = request.env['res.company'].sudo().search([('attendance_kiosk_key', '=', token)])
        return company

    @staticmethod
    def _get_employee_info_response(employee):
        response = {}
        if employee:
            response = {
                'id': employee.id,
                'employee_name': employee.name,
                'employee_avatar': employee.image_1920,
                'hours_today': float_round(employee.hours_today, precision_digits=2),
                'total_overtime': float_round(employee.total_overtime, precision_digits=2),
                'last_attendance_worked_hours': float_round(employee.last_attendance_worked_hours, precision_digits=2),
                'last_check_in': employee.last_check_in,
                'attendance_state': employee.attendance_state,
                'hours_previously_today': float_round(employee.hours_previously_today, precision_digits=2),
                'kiosk_delay': employee.company_id.attendance_kiosk_delay * 1000,
                'attendance': {'check_in': employee.last_attendance_id.check_in,
                               'check_out': employee.last_attendance_id.check_out},
                'overtime_today': request.env['hr.attendance.overtime'].sudo().search([
                    ('employee_id', '=', employee.id), ('date', '=', datetime.date.today()),
                    ('adjustment', '=', False)]).duration or 0,
                'use_pin': employee.company_id.attendance_kiosk_use_pin,
                'display_systray': employee.company_id.attendance_from_systray,
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

    @http.route('/hr_attendance/kiosk_mode_menu', auth='user', type='http')
    def kiosk_menu_item_action(self):
        if request.env.user.user_has_groups("hr_attendance.group_hr_attendance_manager"):
            # Auto log out will prevent users from forgetting to log out of their session
            # before leaving the kiosk mode open to the public. This is a prevention security
            # measure.
            request.session.logout(keep_db=True)
            return request.redirect(request.env.user.company_id.attendance_kiosk_url)
        else:
            return request.not_found()

    @http.route('/hr_attendance/kiosk_keepalive', auth='user', type='json')
    def kiosk_keepalive(self):
        request.session.touch()
        return {}

    @http.route(["/hr_attendance/<token>"], type='http', auth='public', website=True, sitemap=True)
    def open_kiosk_mode(self, token):
        company = self._get_company(token)
        if not company:
            return request.not_found()
        else:
            employee_list = [{"id": e["id"],
                              "name": e["name"],
                              "avatar": e["avatar_1024"].decode(),
                              "job": e["job_id"][1] if e["job_id"] else False,
                              "department": {"id": e["department_id"][0] if e["department_id"] else False,
                                             "name": e["department_id"][1] if e["department_id"] else False
                                             }
                              } for e in request.env['hr.employee'].sudo().search_read(domain=[('company_id', '=', company.id)],
                                                                                       fields=["id",
                                                                                               "name",
                                                                                               "avatar_1024",
                                                                                               "job_id",
                                                                                               "department_id"])]
            departement_list = [{'id': dep["id"],
                                 'name': dep["name"],
                                 'count': dep["total_employee"]
                                 } for dep in request.env['hr.department'].sudo().search_read(domain=[('company_id', '=', company.id)],
                                                                                              fields=["id",
                                                                                                      "name",
                                                                                                      "total_employee"])]
            request.session.logout(keep_db=True)
            return request.render(
                'hr_attendance.public_kiosk_mode',
                {
                    'kiosk_backend_info': {
                        'token': token,
                        'company_id': company.id,
                        'company_name': company.name,
                        'employees': employee_list,
                        'departments': departement_list,
                        'kiosk_mode': company.attendance_kiosk_mode,
                        'barcode_source': company.attendance_barcode_source
                    }
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
        return self._get_employee_info_response(employee)
