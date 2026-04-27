# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    project_id = fields.Many2one(domain="['|', ('company_id', '=', False), '&', ('company_id', '=?', company_id), ('company_id', '=', current_company_id), ('allow_billable', '=', True), '|', ('pricing_type', '=', 'task_rate'), ('is_fsm', '=', True), ('allow_timesheets', 'in', [service_policy == 'delivered_timesheet', True])]")

    @api.constrains('service_type', 'type', 'invoice_policy')
    def _ensure_service_linked_to_project(self):
        read_group_args = {
            'domain': [('timesheet_product_id', 'in', self.product_variant_ids.ids)],
            'fields': ['timesheet_product_id'],
            'groupby': ['timesheet_product_id'],
        }
        product_group = self.env['project.project'].read_group(**read_group_args) + self.env['project.sale.line.employee.map'].read_group(**read_group_args)
        product_ids = [next(iter(vals['timesheet_product_id'])) for vals in product_group]
        templates = self.search([('product_variant_ids', 'in', product_ids)]).filtered(
            lambda template:
                template.service_type != 'timesheet'
                or template.type != 'service'
                or template.invoice_policy != 'delivery'
        )
        if templates:
            separator = "\n -   "
            names = separator + separator.join(templates.mapped('name'))
            raise ValidationError(_("The following products are currently associated with a Field Service project, you cannot change their Invoicing Policy or Type:%s", names))
