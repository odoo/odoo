# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo import api, fields, SUPERUSER_ID, _


def create_internal_project(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies_with_internal = env['project.project'].read_group([
        ('name', '=', _('Internal')), ('allow_timesheets', '=', True)
    ], ['company_id'], ['company_id'])
    company_ids_with_internal = [c['company_id'][0] for c in companies_with_internal]
    for company in env['res.company'].search([('id', 'not in', company_ids_with_internal)]):
        company = company.with_company(company)
        internal_project = company.env['project.project'].create({
            'name': _('Internal'),
            'allow_timesheets': True,
            'company_id': company.id,
        })
        admin = env.ref('base.user_admin', raise_if_not_found=False)
        if not admin:
            continue
        tasks = company.env['project.task'].create([{
            'name': _('Training'),
            'project_id': internal_project.id,
            'company_id': company.id,
        }, {
            'name': _('Meeting'),
            'project_id': internal_project.id,
            'company_id': company.id,
        }])

        if not admin.employee_ids.filtered(lambda e: e.company_id == company):
            continue
        company.env['account.analytic.line'].create([{
            'name': _("Analysis"),
            'user_id': admin.id,
            'date': fields.datetime.today(),
            'unit_amount': 0,
            'project_id': internal_project.id,
            'task_id': task.id,
        } for task in tasks])
