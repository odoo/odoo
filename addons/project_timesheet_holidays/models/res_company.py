# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Company(models.Model):
    _inherit = 'res.company'

    leave_timesheet_project_id = fields.Many2one(
        'project.project', string="Internal Project",
        help="Default project value for timesheet generated from time off type.")
    leave_timesheet_task_id = fields.Many2one(
        'project.task', string="Time Off Task",
        domain="[('project_id', '=', leave_timesheet_project_id)]")

    @api.constrains('leave_timesheet_project_id')
    def _check_leave_timesheet_project_id_company(self):
        for company in self:
            if company.leave_timesheet_project_id:
                if company.leave_timesheet_project_id.sudo().company_id != company:
                    raise ValidationError(_('The Internal Project of a company should be in that company.'))

    def init(self):
        for company in self.search([('leave_timesheet_project_id', '=', False)]):
            company = company.with_company(company)
            project = company.env['project.project'].search([
                ('name', '=', _('Internal')),
                ('allow_timesheets', '=', True),
                ('company_id', '=', company.id),
            ], limit=1)
            if not project:
                project = company.env['project.project'].create({
                    'name': _('Internal'),
                    'allow_timesheets': True,
                    'company_id': company.id,
                })
            company.write({
                'leave_timesheet_project_id': project.id,
            })
            if not company.leave_timesheet_task_id:
                task = company.env['project.task'].create({
                    'name': _('Time Off'),
                    'project_id': company.leave_timesheet_project_id.id,
                    'active': False,
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
            if not company.leave_timesheet_project_id:
                company.write({
                    'leave_timesheet_project_id': project.id,
                })
            if not company.leave_timesheet_task_id:
                task = company.env['project.task'].sudo().create({
                    'name': _('Time Off'),
                    'project_id': company.leave_timesheet_project_id.id,
                    'active': False,
                    'company_id': company.id,
                })
                company.write({
                    'leave_timesheet_task_id': task.id,
                })
