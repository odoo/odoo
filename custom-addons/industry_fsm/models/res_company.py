# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models, api, _


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    def _get_field_service_project_values(self):
        project_name = _("Field Service")
        stage_ids = self.env['ir.model.data'].sudo().search_read([('module', '=', 'industry_fsm'), ('name', 'like', 'planning_project_stage_')], ['res_id'])
        type_ids = [Command.link(stage_id['res_id']) for stage_id in stage_ids]
        return [{
            'name': project_name,
            'is_fsm': True,
            'allow_timesheets': True,
            'type_ids': type_ids,
            'company_id': company.id
        } for company in self]

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        self.env['project.project'].sudo().create(companies._get_field_service_project_values())
        return companies
