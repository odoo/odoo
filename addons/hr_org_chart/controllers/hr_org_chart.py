# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class HrOrgChartController(http.Controller):
    _managers_level = 5  # FP request

    def _check_employee(self, employee_id):
        if not employee_id:  # to check
            return None
        employee_id = int(employee_id)

        Employee = request.env['hr.employee']
        # check and raise
        if not Employee.check_access_rights('read', raise_exception=False):
            return None
        try:
            Employee.browse(employee_id).check_access_rule('read')
        except AccessError:
            return None
        else:
            return Employee.browse(employee_id)

    def _prepare_employee_data(self, employee):
        job = employee.sudo().job_id
        return dict(
            id=employee.id,
            name=employee.name,
            link='/mail/view?model=hr.employee&res_id=%s' % employee.id,
            job_id=job.id,
            job_name=job.name or '',
            direct_sub_count=len(employee.child_ids),
            indirect_sub_count=employee.child_all_count,
        )

    @http.route('/hr/get_org_chart', type='json', auth='user')
    def get_org_chart(self, employee_id):

        employee = self._check_employee(employee_id)
        if not employee:  # to check
            return {}

        # compute employee data for org chart
        ancestors, current = request.env['hr.employee'], employee
        while current.parent_id and len(ancestors) < self._managers_level+1:
            ancestors += current.parent_id
            current = current.parent_id

        values = dict(
            self=self._prepare_employee_data(employee),
            managers=[
                self._prepare_employee_data(ancestor)
                for idx, ancestor in enumerate(ancestors)
                if idx < self._managers_level
            ],
            managers_more=len(ancestors) > self._managers_level,
            children=[self._prepare_employee_data(child) for child in employee.child_ids],
        )
        values['managers'].reverse()
        return values

    @http.route('/hr/get_subordinates', type='json', auth='user')
    def get_subordinates(self, employee_id, subordinates_type=None):
        """
        Get employee subordinates.
        Possible values for 'subordinates_type':
            - 'indirect'
            - 'direct'
        """

        employee = self._check_employee(employee_id)
        if not employee:  # to check
            return {}

        if subordinates_type == 'direct':
            return employee.child_ids.ids
        elif subordinates_type == 'indirect':
            return (employee.subordinate_ids - employee.child_ids).ids
        else:
            return employee.subordinate_ids.ids
