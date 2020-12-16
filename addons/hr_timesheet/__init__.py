# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo import api, fields, SUPERUSER_ID, _


def create_internal_project(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # allow_timesheets is set by default, but erased for existing projects at
    # installation, as there is no analytic account for them.
    env['project.project'].search([]).write({'allow_timesheets': True})

    admin = env.ref('base.user_admin', raise_if_not_found=False)
    if not admin:
        return
    project_vals = []
    for company in env['res.company'].search([]):
        company = company.with_company(company)
        project_vals += [{
            'name': _('Internal'),
            'allow_timesheets': True,
            'company_id': company.id,
            'task_ids': [(0, 0, {
                'name': name,
                'company_id': company.id,
            }) for name in [_('Training'), _('Meeting')]]
        }]
    project_ids = env['project.project'].create(project_vals)

    env['account.analytic.line'].create([{
        'name': _("Analysis"),
        'user_id': admin.id,
        'date': fields.datetime.today(),
        'unit_amount': 0,
        'project_id': task.project_id.id,
        'task_id': task.id,
    } for task in project_ids.task_ids.filtered(lambda t: t.company_id in admin.employee_ids.company_id)])
