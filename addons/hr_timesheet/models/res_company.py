# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _default_project_time_mode_id(self):
        return self.env.ref('uom.product_uom_hour', raise_if_not_found=False)

    @api.model
    def _default_timesheet_encode_uom_id(self):
        return self.env.ref('uom.product_uom_hour', raise_if_not_found=False)

    project_time_mode_id = fields.Many2one('uom.uom', string='Project Time Unit',
        default=_default_project_time_mode_id,
        help="This will set the unit of measure used in projects and tasks.\n"
             "If you use the timesheet linked to projects, don't "
             "forget to setup the right unit of measure in your employees.")
    timesheet_encode_uom_id = fields.Many2one('uom.uom', string="Timesheet Encoding Unit",
        default=_default_timesheet_encode_uom_id)
    internal_project_id = fields.Many2one(
        "project.project", string="Internal Project",
        domain=[("is_template", "=", False)],
        help="Default project value for timesheet generated from time off type.",
    )

    @api.constrains('internal_project_id')
    def _check_internal_project_id_company(self):
        if self.filtered(lambda company: company.internal_project_id and company.internal_project_id.sudo().company_id != company):
            raise ValidationError(_('The Internal Project of a company should be in that company.'))

    @api.model_create_multi
    def create(self, vals_list):
        company = super().create(vals_list)
        # use sudo as the user could have the right to create a company
        # but not to create a project. On the other hand, when the company
        # is created, it is not in the allowed_company_ids on the env
        company.sudo()._create_internal_project_task()
        return company

    def _create_internal_project_task(self):
        results = []
        type_ids_ref = self.env.ref('hr_timesheet.internal_project_default_stage', raise_if_not_found=False)
        type_ids = [(4, type_ids_ref.id)] if type_ids_ref else []
        for company in self:
            company = company.with_company(company)
            results += [{
                'name': _('Internal'),
                'allow_timesheets': True,
                'company_id': company.id,
                'type_ids': type_ids,
                'task_ids': [(0, 0, {
                    'name': name,
                    'company_id': company.id,
                }) for name in [_('Training'), _('Meeting')]]
            }]
        project_ids = self.env['project.project'].create(results)
        projects_by_company = {project.company_id.id: project for project in project_ids}
        for company in self:
            company.internal_project_id = projects_by_company.get(company.id, False)
        return project_ids
