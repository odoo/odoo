# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ProjectMilestone(models.Model):
    _name = 'project.milestone'
    _inherit = 'project.milestone'

    def _default_sale_line_id(self):
        project_id = self._context.get('default_project_id')
        if not project_id:
            return []
        project = self.env['project.project'].browse(project_id)
        return self.env['sale.order.line'].search([
            ('order_id', '=', project.sale_order_id.id),
            ('qty_delivered_method', '=', 'milestones'),
        ], limit=1)

    allow_billable = fields.Boolean(related='project_id.allow_billable', export_string_translation=False)
    project_partner_id = fields.Many2one(related='project_id.partner_id', export_string_translation=False)

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Item', default=_default_sale_line_id, help='Sales Order Item that will be updated once the milestone is reached.',
        domain="[('order_partner_id', '=?', project_partner_id), ('qty_delivered_method', '=', 'milestones')]")
    quantity_percentage = fields.Float('Quantity (%)', compute="_compute_quantity_percentage", store=True, help='Percentage of the ordered quantity that will automatically be delivered once the milestone is reached.')

    sale_line_display_name = fields.Char("Sale Line Display Name", related='sale_line_id.display_name', export_string_translation=False)
    product_uom = fields.Many2one(related="sale_line_id.product_uom", export_string_translation=False)
    product_uom_qty = fields.Float("Quantity", compute="_compute_product_uom_qty", readonly=False)

    @api.depends('sale_line_id.product_uom_qty', 'product_uom_qty')
    def _compute_quantity_percentage(self):
        for milestone in self:
            milestone.quantity_percentage = milestone.sale_line_id.product_uom_qty and milestone.product_uom_qty / milestone.sale_line_id.product_uom_qty

    @api.depends('sale_line_id', 'quantity_percentage')
    def _compute_product_uom_qty(self):
        for milestone in self:
            if milestone.quantity_percentage:
                milestone.product_uom_qty = milestone.quantity_percentage * milestone.sale_line_id.product_uom_qty
            else:
                milestone.product_uom_qty = milestone.sale_line_id.product_uom_qty

    @api.model
    def _get_fields_to_export(self):
        return super()._get_fields_to_export() + ['allow_billable', 'quantity_percentage', 'sale_line_display_name']

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_line_id.order_id.id,
            'view_mode': 'form',
        }
