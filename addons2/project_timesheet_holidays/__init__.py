# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init(env):
    """ Set the timesheet project and task on existing leave type. Do it in post_init to
        be sure the internal project/task of res.company are set. (Since timesheet_generate field
        is true by default, those 2 fields are required on the leave type).
    """
    for hr_leave_type in env['hr.leave.type'].search([('timesheet_generate', '=', True), ('company_id', '!=', False), ('timesheet_project_id', '=', False)]):
        project_id = hr_leave_type.company_id.internal_project_id
        default_task_id = hr_leave_type.company_id.leave_timesheet_task_id
        hr_leave_type.write({
            'timesheet_project_id': project_id.id,
            'timesheet_task_id': default_task_id.id if default_task_id and default_task_id.project_id == project_id else False,
        })
