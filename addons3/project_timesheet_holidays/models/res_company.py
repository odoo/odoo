# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class Company(models.Model):
    _inherit = 'res.company'

    leave_timesheet_task_id = fields.Many2one(
        'project.task', string="Time Off Task",
        domain="[('project_id', '=', internal_project_id)]")

    def init(self):
        type_ids = [(4, self.env.ref('hr_timesheet.internal_project_default_stage').id)]
        companies = self.search(['|', ('internal_project_id', '=', False), ('leave_timesheet_task_id', '=', False)])
        internal_projects_by_company_dict = None
        Project = self.env['project.project']
        for company in companies:
            company = company.with_company(company)
            if not company.internal_project_id:
                if not internal_projects_by_company_dict:
                    internal_projects_by_company_read = Project.search_read([
                        ('name', '=', _('Internal')),
                        ('allow_timesheets', '=', True),
                        ('company_id', 'in', companies.ids),
                    ], ['company_id', 'id'])
                    internal_projects_by_company_dict = {res['company_id'][0]: res['id'] for res in internal_projects_by_company_read}
                project_id = internal_projects_by_company_dict.get(company.id, False)
                if not project_id:
                    project_id = Project.create({
                        'name': _('Internal'),
                        'allow_timesheets': True,
                        'company_id': company.id,
                        'type_ids': type_ids,
                    }).id
                company.write({'internal_project_id': project_id})
            if not company.leave_timesheet_task_id:
                task = company.env['project.task'].create({
                    'name': _('Time Off'),
                    'project_id': company.internal_project_id.id,
                    'active': True,
                    'company_id': company.id,
                })
                company.write({
                    'leave_timesheet_task_id': task.id,
                })

    def _create_internal_project_task(self):
        projects = super()._create_internal_project_task()
        for project in projects:
            company = project.company_id
            company = company.with_company(company)
            if not company.leave_timesheet_task_id:
                task = company.env['project.task'].sudo().create({
                    'name': _('Time Off'),
                    'project_id': company.internal_project_id.id,
                    'active': True,
                    'company_id': company.id,
                })
                company.write({
                    'leave_timesheet_task_id': task.id,
                })
        return projects
