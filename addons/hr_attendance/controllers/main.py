# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

from werkzeug.exceptions import Forbidden


class HrAttendance(http.Controller):
    @http.route('/hr_attendance/kiosk_keepalive', auth='user', type='json')
    def kiosk_keepalive(self):
        request.session.touch()
        return {}

    @http.route('/kiosk', auth='user')
    def attendance_kiosk(self):
        if not request.env.user.has_group('hr_attendance.group_hr_attendance_kiosk'):
            raise Forbidden()
        menu = request.env.ref('hr_attendance.menu_hr_attendance_kiosk')
        return request.redirect(f'/web#menu_id={menu.id}&action_id={menu.action.id}')
