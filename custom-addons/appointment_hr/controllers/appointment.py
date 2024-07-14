# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.appointment.controllers.appointment import AppointmentController
from odoo.http import request, route


class AppointmentHr(AppointmentController):

    # ------------------------------------------------------------
    # APPOINTMENT TYPE PAGE VIEW
    # ------------------------------------------------------------

    @route()
    def appointment_type_page(self, appointment_type_id, state=False, **kwargs):

        if not kwargs.get('filter_staff_user_ids'):
            appointment_type = request.env['appointment.type'].sudo().browse(int(appointment_type_id))
            kwargs['filter_staff_user_ids'] = self._get_filtered_staff_user_ids(
                appointment_type,
                kwargs.get('filter_employee_ids'),
                kwargs.get('employee_id'))
        return super().appointment_type_page(appointment_type_id, state, **kwargs)

    def _get_filtered_staff_user_ids(self, appointment_type, filter_employee_ids=None, employee_id=None):
        """ This method returns the ids of suggested users, ensuring retrocompatibility with previous routes.
            These may be cleaned in the future. If several parameters exist, the priority is given to the newest
            route format filter first."""

        # Ensure old link ?filter_employee_ids= retrocompatibility. This parameter is deprecated since task-2499566.
        filter_employee_ids = json.loads(filter_employee_ids) if filter_employee_ids else []
        if filter_employee_ids:
            employees = request.env['hr.employee'].sudo().browse(filter_employee_ids).exists()
            valid_employees = employees.filtered(lambda emp: emp.user_id in appointment_type.staff_user_ids)
            if valid_employees:
                return str(valid_employees.user_id.ids)

        # Ensure old link ?employee_id= retrocompatibility. This parameter is deprecated since task-2190526.
        if employee_id:
            employee = request.env['hr.employee'].sudo().browse(int(employee_id))
            if employee.exists() and employee.user_id in appointment_type.staff_user_ids:
                return str(employee.user_id.ids)

        return '[]'
