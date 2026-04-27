# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_services_values(self, project):
        services = super()._get_services_values(project)
        if not project.allow_billable:
            return services
        sol_ids = [
            service['sol'].id
            for service in services['data']
        ]
        slots = self.env['planning.slot']._read_group([
            ('project_id', '=', project.id),
            ('sale_line_id', 'in', sol_ids),
            ('start_datetime', '>=', fields.Date.today())
        ], ['sale_line_id'], ['allocated_hours:sum'])
        slots_by_order_line = {sale_line.id: allocated_hours_sum for sale_line, allocated_hours_sum in slots}
        uom_hour = self.env.ref('uom.product_uom_hour')
        for service in services['data']:
            if service['is_unit']:
                continue
            allocated_hours = uom_hour._compute_quantity(slots_by_order_line.get(service['sol'].id, 0), self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
            service['planned_value'] = allocated_hours
            service['remaining_value'] = service['remaining_value'] - allocated_hours
        return services
