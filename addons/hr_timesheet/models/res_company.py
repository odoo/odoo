# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, values):
        company = super(ResCompany, self).create(values)
        # use sudo as the user could have the right to create a company
        # but not to create a project. On the other hand, when the company
        # is created, it is not in the allowed_company_ids on the env
        company.sudo()._create_internal_project_task()
        return company

    def _create_internal_project_task(self):
        results = []
        type_ids = [(4, self.env.ref('hr_timesheet.internal_project_default_stage').id)]
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
        return project_ids
