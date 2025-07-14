# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_allow_out_of_stock_order = fields.Boolean(
        string="Continue selling when out-of-stock",
        default=True,
        default_model='product.template',
    )
    default_available_threshold = fields.Float(
        string="Show Threshold",
        default=5.0,
        default_model='product.template',
    )
    default_show_availability = fields.Boolean(
        string="Show availability Qty",
        default=False,
        default_model='product.template',
    )
    website_warehouse_id = fields.Many2one(
        'stock.warehouse',
        related='website_id.warehouse_id',
        domain="[('company_id', '=', website_company_id)]",
        readonly=False,
    )
