# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # RENTAL company defaults :

    # Extra Costs

    extra_hour = fields.Float(
        "Per Hour", related="company_id.extra_hour", readonly=False,
        help="This is the default extra cost per hour set on newly created products. You can change this value for existing products directly on the product itself.")
    extra_day = fields.Float(
        "Per Day", related="company_id.extra_day", readonly=False,
        help="This is the default extra cost per day set on newly created products. You can change this value for existing products directly on the product itself.")
    # extra_week = fields.Monetary("Extra Week")
    min_extra_hour = fields.Integer("Minimum delay time before applying fines.", related="company_id.min_extra_hour", readonly=False)
    # week uom disabled in rental for the moment
    extra_product = fields.Many2one(
        'product.product', string="Delay Product",
        help="This product will be used to add fines in the Rental Order.", related="company_id.extra_product",
        readonly=False, domain="[('type', '=', 'service')]")

    module_sale_renting_sign = fields.Boolean(string="Digital Documents")

    @api.onchange('extra_hour')
    def _onchange_extra_hour(self):
        self.env['ir.property']._set_default("extra_hourly", "product.template", self.extra_hour)

    @api.onchange('extra_day')
    def _onchange_extra_day(self):
        self.env['ir.property']._set_default("extra_daily", "product.template", self.extra_day)
