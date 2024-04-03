# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProjectMilestone(models.Model):
    _name = 'project.milestone'
    _inherit = 'project.milestone'

    allow_billable = fields.Boolean(related='project_id.allow_billable')
    project_partner_id = fields.Many2one(related='project_id.partner_id')

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Item', help='Sales Order Item that will be updated once the milestone is reached.',
        domain="[('order_partner_id', '=?', project_partner_id), ('qty_delivered_method', '=', 'milestones')]")
    quantity_percentage = fields.Float('Quantity', help='Percentage of the ordered quantity that will automatically be delivered once the milestone is reached.')

    sale_line_name = fields.Text(related='sale_line_id.name')

    @api.model
    def _get_fields_to_export(self):
        return super()._get_fields_to_export() + ['allow_billable', 'quantity_percentage', 'sale_line_name']
