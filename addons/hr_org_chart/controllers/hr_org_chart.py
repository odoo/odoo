# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class HrOrgChartController(http.Controller):
    _managers_level = 2  # FP request

    def _prepare_employee_data(self, employee):
        return dict(
            id=employee.id,
            name=employee.name,
            link='/mail/view?model=hr.employee&res_id=%s' % employee.id,
            job_id=employee.job_id.id,
            job_name=employee.job_id.name or '',
            direct_sub_count=len(employee.child_ids),
            indirect_sub_count=employee.child_all_count,
        )

    @http.route('/hr/get_org_chart', type='json', auth='user')
    def get_org_chart(self, employee_id):
        if not employee_id:  # to check
            return {}
        employee_id = int(employee_id)

        Employee = request.env['hr.employee']
        # check and raise
        if not Employee.check_access_rights('read', raise_exception=False):
            return {}
        try:
            Employee.browse(employee_id).check_access_rule('read')
        except AccessError:
            return {}
        else:
            employee = Employee.browse(employee_id)

        # compute employee data for org chart
        ancestors, current = request.env['hr.employee'], employee
        while current.parent_id:
            ancestors += current.parent_id
            current = current.parent_id

        values = dict(
            self=self._prepare_employee_data(employee),
            managers=[self._prepare_employee_data(ancestor) for idx, ancestor in enumerate(ancestors) if idx < self._managers_level],
            managers_more=len(ancestors) > self._managers_level,
            children=[self._prepare_employee_data(child) for child in employee.child_ids],
        )
        values['managers'].reverse()
        return values
