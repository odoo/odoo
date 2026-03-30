# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class HrOrgChartController(http.Controller):
    _managers_level = 5  # FP request

    def _check_employee(self, employee_id, **kw):
        employee_id = int(employee_id) if employee_id else False

        if 'allowed_company_ids' in request.env.context:
            cids = request.env.context['allowed_company_ids']
        else:
            cids = [request.env.company.id]

        Employee = request.env['hr.employee.public'].with_context(allowed_company_ids=cids)
        # check and raise
        if not Employee.check_access_rights('read', raise_exception=False):
            return request.env['hr.employee.public']
        try:
            Employee.browse(employee_id).check_access_rule('read')
        except AccessError:
            return request.env['hr.employee.public']
        else:
            return Employee.browse(employee_id)

    def _prepare_employee_data(self, employee):
        job = employee.sudo().job_id
        return dict(
            id=employee.id,
            name=employee.name,
            link='/mail/view?model=%s&res_id=%s' % ('hr.employee.public', employee.id,),
            job_id=job.id,
            job_name=job.name or '',
            job_title=employee.job_title or '',
            direct_sub_count=len(employee.child_ids - employee),
            indirect_sub_count=employee.child_all_count,
        )

    @http.route('/hr/get_redirect_model', type='json', auth='user')
    def get_redirect_model(self):
        if request.env['hr.employee'].check_access_rights('read', raise_exception=False):
            return 'hr.employee'
        return 'hr.employee.public'

    @http.route('/hr/get_org_chart', type='json', auth='user')
    def get_org_chart(self, employee_id, **kw):
        employee = self._check_employee(employee_id, **kw)
        new_parent_id = request.env.context.get('new_parent_id', None)
        new_parent = self._check_employee(new_parent_id, **kw)
        if not employee:  # to check
            return {
                'managers': [],
                'children': [],
            }

        # compute employee data for org chart
        ancestors, current = request.env['hr.employee.public'].sudo(), employee.sudo()
        current_parent = new_parent if new_parent_id is not None else current.parent_id
        max_level = (request.env.context.get('max_level', None) or self._managers_level) + 1
        while current_parent and current != current_parent and employee.sudo() != current_parent and len(ancestors) < max_level:
            current = current_parent
            current_parent = current.parent_id if current != employee or not new_parent else new_parent
            if current_parent in ancestors:
                break
            else:
                ancestors += current

        values = dict(
            self=self._prepare_employee_data(employee),
            managers=[
                self._prepare_employee_data(ancestor)
                for idx, ancestor in enumerate(ancestors)
                if idx < max_level - 1
            ],
            managers_more=len(ancestors) > self._managers_level,
            children=[self._prepare_employee_data(child) for child in employee.child_ids if child != employee],
        )
        values['managers'].reverse()
        return values

    @http.route('/hr/get_subordinates', type='json', auth='user')
    def get_subordinates(self, employee_id, subordinates_type=None, **kw):
        """
        Get employee subordinates.
        Possible values for 'subordinates_type':
            - 'indirect'
            - 'direct'
        """
        employee = self._check_employee(employee_id, **kw)
        if not employee:  # to check
            return {}

        if subordinates_type == 'direct':
            res = (employee.child_ids - employee).ids
        elif subordinates_type == 'indirect':
            res = (employee.subordinate_ids - employee.child_ids).ids
        else:
            res = employee.subordinate_ids.ids

        return res
