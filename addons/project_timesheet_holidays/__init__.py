# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init(cr, registry):
    """ Set the timesheet project and task on existing leave type. Do it in post_init to
        be sure the internal project/task of res.company are set. (Since timesheet_generate field
        is true by default, those 2 fields are required on the leave type).
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    for hr_leave_type in env['hr.leave.type'].search([('timesheet_generate', '=', True), ('timesheet_project_id', '=', False)]):
        company = hr_leave_type.company_id or env.company
        hr_leave_type.write({
            'timesheet_project_id': company.leave_timesheet_project_id.id,
            'timesheet_task_id': company.leave_timesheet_task_id.id,
        })
