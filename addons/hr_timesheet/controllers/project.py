# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.osv import expression

from odoo.addons.project.controllers.portal import CustomerPortal


class ProjectCustomerPortal(CustomerPortal):

    def _get_project_sharing_company(self, project):
        company = project.company_id
        if not company:
            timesheet = request.env['account.analytic.line'].sudo().search([('project_id', '=', project.id)], limit=1)
            company = timesheet.company_id or request.env.user.company_id
        return company

    def _prepare_project_sharing_session_info(self, project, task=None):
        session_info = super()._prepare_project_sharing_session_info(project, task)
        company = request.env['res.company'].sudo().browse(session_info['user_companies']['current_company'])
        timesheet_encode_uom = company.timesheet_encode_uom_id
        project_time_mode_uom = company.project_time_mode_id

        session_info['user_companies']['allowed_companies'][company.id].update(
            timesheet_uom_id=timesheet_encode_uom.id,
            timesheet_uom_factor=project_time_mode_uom._compute_quantity(
                1.0,
                timesheet_encode_uom,
                round=False
            ),
        )
        session_info['uom_ids'] = {
            uom.id:
                {
                    'id': uom.id,
                    'name': uom.name,
                    'rounding': uom.rounding,
                    'timesheet_widget': uom.timesheet_widget,
                } for uom in [timesheet_encode_uom, project_time_mode_uom]
        }
        session_info['action_context']['allow_timesheets'] = project.allow_timesheets
        return session_info

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super(ProjectCustomerPortal, self)._task_get_page_view_values(task, access_token, **kwargs)
        domain = request.env['account.analytic.line']._timesheet_get_portal_domain()
        task_domain = expression.AND([domain, [('task_id', '=', task.id)]])
        timesheets = request.env['account.analytic.line'].sudo().search(task_domain)

        values['allow_timesheets'] = task.allow_timesheets
        values['timesheets'] = timesheets
        values['is_uom_day'] = request.env['account.analytic.line']._is_timesheet_encode_uom_day()
        return values
