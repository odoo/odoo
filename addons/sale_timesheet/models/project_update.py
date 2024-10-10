# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        template_values = super()._get_template_values(project)
        services_data = template_values.setdefault('services', {'data': []}).setdefault('data', [])
        additional_services = self._get_additional_services_values(project)
        unique_services = [
            service for service in additional_services.get('data', [])
            if service['sol'] not in {existing_service['sol'] for existing_service in services_data}
        ]
        services_data[:] = unique_services + services_data
        template_values['show_sold'] = bool(services_data)
        return template_values

    @api.model
    def _get_additional_services_values(self, project):
        if not project.allow_billable:
            return {'data': []}
        company_uom = self.env.company.timesheet_encode_uom_id if hasattr(self.env.company, 'timesheet_encode_uom_id') else self.env.ref('uom.product_uom_unit')
        services = self._get_common_services_values(project, company_uom)
        return {
            'data': services,
            'company_unit_name': company_uom.name,
        }

    @api.model
    def _get_profitability_values(self, project):
        if not project.allow_billable:
            return {}
        return super()._get_profitability_values(project)
