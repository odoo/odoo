# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ApprovalProductLine(models.Model):
    _name = 'approval.product.line'
    _description = 'Product Line'

    _check_company_auto = True

    approval_request_id = fields.Many2one('approval.request', required=True)
    description = fields.Char(
        "Description", required=True,
        compute="_compute_description", store=True, readonly=False, precompute=True)
    company_id = fields.Many2one(
        string='Company', related='approval_request_id.company_id',
        store=True, readonly=True, index=True)
    product_id = fields.Many2one('product.product', string="Products", check_company=True)
    product_uom_id = fields.Many2one(
        'uom.uom', string="Unit of Measure",
        compute="_compute_product_uom_id", store=True, readonly=False, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    quantity = fields.Float("Quantity", default=1.0)

    @api.depends('product_id')
    def _compute_description(self):
        for line in self:
            line.description = line.product_id.description_purchase or line.product_id.display_name

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id
