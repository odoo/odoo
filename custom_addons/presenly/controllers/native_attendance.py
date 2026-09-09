from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.hr_attendance.controllers.main import HrAttendance as NativeHrAttendance


class PresenlyNativeAttendanceDisabled(NativeHrAttendance):
    """Disable native attendance channels without changing company data.

    Presenly's authenticated mobile API remains independent of these routes.
    The central ``hr.employee._attendance_action_change`` guard provides a
    second layer in case another native caller attempts the same mutation.
    """

    @http.route()
    def kiosk_menu_item_action(self, company_id):
        return request.not_found()

    @http.route()
    def get_employees_without_badge(self, token, name=None, limit=20):
        return {}

    @http.route()
    def set_badge(self, employee_id, badge, token):
        return {}

    @http.route()
    def create_employee(self, name, token):
        return False

    @http.route()
    def kiosk_keepalive(self):
        return {}

    @http.route()
    def open_kiosk_mode(self, token, from_trial_mode=False):
        return request.not_found()

    @http.route()
    def employee_attendance_data(self, token, employee_id):
        return {}

    @http.route()
    def scan_barcode_with_geolocation(
        self, token, barcode, latitude=False, longitude=False,
    ):
        return {}

    @http.route()
    def manual_selection(
        self, token, employee_id, pin_code, latitude=False, longitude=False,
    ):
        return {}

    @http.route()
    def employees_infos(self, token, limit, offset, domain):
        return {'records': [], 'length': 0}

    @http.route()
    def systray_attendance(self, latitude=False, longitude=False):
        raise UserError(_(
            'Native Odoo check-in and check-out are disabled. '
            'Use the Presenly mobile application.'
        ))

    @http.route()
    def user_attendance_data(self):
        data = super().user_attendance_data()
        data['display_systray'] = False
        return data

    @http.route()
    def set_attendance_settings(self, token, mode):
        return False
