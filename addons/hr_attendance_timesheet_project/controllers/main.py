# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.tools import float_round
from odoo.tools.image import image_data_uri
import datetime
import logging

_logger = logging.getLogger(__name__)


class HrAttendanceTimesheetProject(http.Controller):

    @staticmethod
    def _get_company(token):
        """Get company from kiosk token"""
        company = request.env['res.company'].sudo().search([('attendance_kiosk_key', '=', token)])
        return company

    @staticmethod
    def _get_employee_info_response(employee):
        """Get employee info response similar to hr_attendance controller"""
        response = {}
        if employee:
            # Get current project info from active timesheet
            current_attendance = employee.last_attendance_id
            current_project_name = None
            if current_attendance and not current_attendance.check_out and current_attendance.active_timesheet_id:
                if current_attendance.active_timesheet_id.project_id:
                    current_project_name = current_attendance.active_timesheet_id.project_id.name

            response = {
                'id': employee.id,
                'employee_name': employee.name,
                'employee_avatar': employee.image_256 and image_data_uri(employee.image_256),
                'hours_today': float_round(employee.hours_today, precision_digits=2),
                'hours_previously_today': float_round(employee.hours_previously_today, precision_digits=2),
                'last_attendance_worked_hours': float_round(employee.last_attendance_worked_hours, precision_digits=2),
                'last_check_in': employee.last_check_in,
                'attendance_state': employee.attendance_state,
                'total_overtime': float_round(employee.total_overtime, precision_digits=2),
                'kiosk_delay': employee.company_id.attendance_kiosk_delay * 1000,
                'attendance': {
                    'check_in': employee.last_attendance_id.check_in,
                    'check_out': employee.last_attendance_id.check_out
                },
                'current_project_name': current_project_name,
                'display_systray': employee.company_id.attendance_from_systray,
                'device_tracking_enabled': employee.company_id.attendance_device_tracking,
                'use_pin': employee.company_id.attendance_kiosk_use_pin,
                'display_overtime': employee.company_id.hr_attendance_display_overtime,
            }
        return response

    @http.route('/hr_attendance/kiosk_check_employee_status', type='jsonrpc', auth='public')
    def kiosk_check_employee_status(self, token, barcode=None, employee_id=None):
        """
        Check employee status WITHOUT toggling attendance.
        Used to determine if we should show action choice dialog.
        """
        _logger.info("[Kiosk] check_employee_status called - barcode: %s, employee_id: %s", barcode, employee_id)
        company = self._get_company(token)
        if not company:
            _logger.warning("[Kiosk] No company found for token")
            return {}

        # Find employee by barcode or ID
        if barcode:
            employee = request.env['hr.employee'].sudo().search([
                ('barcode', '=', barcode),
                ('company_id', '=', company.id)
            ], limit=1)
        elif employee_id:
            employee = request.env['hr.employee'].sudo().browse(employee_id)
            if employee.company_id != company:
                return {}
        else:
            return {}

        if not employee:
            _logger.warning("[Kiosk] No employee found")
            return {}

        # Get current attendance info
        current_attendance = employee.last_attendance_id
        current_project_name = None
        attendance_id = None

        if current_attendance and not current_attendance.check_out:
            # Employee is checked in
            attendance_id = current_attendance.id
            # Get project from active timesheet
            if current_attendance.active_timesheet_id and current_attendance.active_timesheet_id.project_id:
                current_project_name = current_attendance.active_timesheet_id.project_id.name

        result = {
            'employee_id': employee.id,
            'employee_name': employee.name,
            'attendance_state': employee.attendance_state,
            'attendance_id': attendance_id,
            'current_project_name': current_project_name,
        }
        _logger.info("[Kiosk] check_employee_status result: %s", result)
        return result

    @http.route('/hr_attendance/kiosk_get_employee_projects', type='jsonrpc', auth='public')
    def kiosk_get_employee_projects(self, employee_id):
        """
        Get list of available projects for employee to choose from.
        Returns all projects that allow timesheets.
        """
        _logger.info("[Kiosk] get_employee_projects called for employee: %s", employee_id)
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee:
            _logger.warning("[Kiosk] Employee %s not found", employee_id)
            return {'projects': []}

        # Get all projects that allow timesheets
        projects = request.env['project.project'].sudo().search([
            ('allow_timesheets', '=', True),
            ('active', '=', True),
        ])

        project_list = [{
            'id': project.id,
            'name': project.name,
            'partner_name': project.partner_id.name if project.partner_id else '',
        } for project in projects]

        return {'projects': project_list}

    @http.route('/hr_attendance/kiosk_change_project', type='jsonrpc', auth='public')
    def kiosk_change_project(self, attendance_id, project_id):
        """
        Change project for current attendance WITHOUT checking out.
        Uses the change_project_to method from hr.attendance model.
        """
        _logger.info("[Kiosk] change_project called - attendance: %s, project: %s", attendance_id, project_id)
        attendance = request.env['hr.attendance'].sudo().browse(attendance_id)
        if not attendance or attendance.check_out:
            _logger.warning("[Kiosk] Attendance not found or already checked out")
            return {'success': False, 'error': _('Attendance not found or already checked out')}

        project = request.env['project.project'].sudo().browse(project_id)
        if not project:
            _logger.warning("[Kiosk] Project %s not found", project_id)
            return {'success': False, 'error': _('Project not found')}

        try:
            # Call the change_project_to method from our module
            attendance.change_project_to(project_id)
            _logger.info("[Kiosk] Project changed successfully to %s", project.name)
            return {
                'success': True,
                'project_name': project.name,
            }
        except Exception as e:
            _logger.error("[Kiosk] Error changing project: %s", str(e), exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/hr_attendance/kiosk_checkout', type='jsonrpc', auth='public')
    def kiosk_checkout(self, token, attendance_id, latitude=False, longitude=False):
        """
        Perform check-out for the given attendance.
        Similar to normal attendance toggle but explicitly for check-out.
        """
        company = self._get_company(token)
        if not company:
            return {}

        attendance = request.env['hr.attendance'].sudo().browse(attendance_id)
        if not attendance or attendance.check_out:
            return {}

        employee = attendance.employee_id

        # Get geoip info
        geo_ip_response = self._get_geoip_response(
            'kiosk',
            latitude=latitude,
            longitude=longitude,
            device_tracking_enabled=company.attendance_device_tracking
        )

        # Perform check-out by calling _attendance_action_change
        employee.sudo()._attendance_action_change(geo_ip_response)

        return self._get_employee_info_response(employee)

    @http.route('/hr_attendance/kiosk_get_employee_info', type='jsonrpc', auth='public')
    def kiosk_get_employee_info(self, token, employee_id):
        """
        Get employee info after project change (for greeting screen).
        """
        company = self._get_company(token)
        if not company:
            return {}

        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee or employee.company_id != company:
            return {}

        return self._get_employee_info_response(employee)

    @staticmethod
    def _get_geoip_response(mode, latitude=False, longitude=False, device_tracking_enabled=True):
        """Get geoip response - copied from hr_attendance controller"""
        response = {'mode': mode}

        if not device_tracking_enabled:
            return response

        if latitude and longitude:
            geo_obj = request.env['base.geocoder']
            location_request = geo_obj._call_openstreetmap_reverse(latitude, longitude)
            if location_request and location_request.get('display_name'):
                location = location_request.get('display_name')
            else:
                location = _('Unknown')
        else:
            city = request.geoip.city.name
            country = request.geoip.country.name
            if city and country:
                location = f"{city}, {country}"
            else:
                location = _('Unknown')

        response.update({
            'location': location,
            'latitude': latitude or request.geoip.location.latitude or False,
            'longitude': longitude or request.geoip.location.longitude or False,
            'ip_address': request.geoip.ip,
            'browser': request.httprequest.user_agent.browser,
        })

        return response
