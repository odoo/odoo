# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init(env):
    """ Set the timesheet project and task on existing leave type. Do it in post_init to
        be sure the internal project/task of res.company are set. (Since timesheet_generate field
        is true by default, those 2 fields are required on the leave type).
    """
    type_ids_ref = env.ref('hr_timesheet.internal_project_default_stage', raise_if_not_found=False)
    type_ids = [(4, type_ids_ref.id)] if type_ids_ref else []
    companies = env['res.company'].search(['|', ('internal_project_id', '=', False), ('leave_timesheet_task_id', '=', False)])
    internal_projects_by_company_dict = None
    project = env['project.project']
    for company in companies:
        company = company.with_company(company)
        if not company.internal_project_id:
            if not internal_projects_by_company_dict:
                internal_projects_by_company_read = project.search_read([
                    ('name', '=', env._('Internal')),
                    ('allow_timesheets', '=', True),
                    ('company_id', 'in', companies.ids),
                ], ['company_id', 'id'])
                internal_projects_by_company_dict = {res['company_id'][0]: res['id'] for res in internal_projects_by_company_read}
            project_id = internal_projects_by_company_dict.get(company.id, False)
            if not project_id:
                project_id = project.create({
                    'name': env._('Internal'),
                    'allow_timesheets': True,
                    'company_id': company.id,
                    'type_ids': type_ids,
                }).id
            company.write({'internal_project_id': project_id})
        if not company.leave_timesheet_task_id:
            task = company.env['project.task'].create({
                'name': env._('Time Off'),
                'project_id': company.internal_project_id.id,
                'active': True,
                'company_id': company.id,
            })
            company.write({
                'leave_timesheet_task_id': task.id,
            })

    for hr_leave_type in env['hr.leave.type'].search([('timesheet_generate', '=', True), ('company_id', '!=', False), ('timesheet_project_id', '=', False)]):
        project_id = hr_leave_type.company_id.internal_project_id
        default_task_id = hr_leave_type.company_id.leave_timesheet_task_id
        hr_leave_type.write({
            'timesheet_project_id': project_id.id,
            'timesheet_task_id': default_task_id.id if default_task_id and default_task_id.project_id == project_id else False,
        })
