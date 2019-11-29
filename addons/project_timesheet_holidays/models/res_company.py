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
        self.search([('leave_timesheet_project_id', '=', False)])._create_leave_project_task()

    @api.model
    def create(self, values):
        company = super(Company, self).create(values)
        # use sudo as the user could have the right to create a company
        # but not to create a project. On the other hand, when the company
        # is created, it is not in the allowed_company_ids on the env
        company.sudo()._create_leave_project_task()
        return company

    def _create_leave_project_task(self):
        for company in self:
            if not company.leave_timesheet_project_id:
                project = self.env['project.project'].sudo().create({
                    'name': _('Internal Project'),
                    'allow_timesheets': True,
                    'active': False,
                    'company_id': company.id,
                })
                company.write({
                    'leave_timesheet_project_id': project.id,
                })
            if not company.leave_timesheet_task_id:
                task = self.env['project.task'].sudo().create({
                    'name': _('Time Off'),
                    'project_id': company.leave_timesheet_project_id.id,
                    'active': False,
                    'company_id': company.id,
                })
                company.write({
                    'leave_timesheet_task_id': task.id,
                })
