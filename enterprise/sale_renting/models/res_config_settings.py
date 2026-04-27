# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    extra_hour = fields.Float(
        string="Per Hour",
        help="This is the default extra cost per hour set on newly created products."
             "You can change this value for existing products directly on the product itself.",
        compute='_compute_extra_hour',
        inverse='_inverse_extra_hour',
    )
    extra_day = fields.Float(
        string="Per Day",
        help="This is the default extra cost per day set on newly created products."
             "You can change this value for existing products directly on the product itself.",
        compute='_compute_extra_day',
        inverse='_inverse_extra_day',
    )
    min_extra_hour = fields.Integer(
        string="Minimum delay time before applying fines.",
        related='company_id.min_extra_hour',
        readonly=False,
    )
    extra_product = fields.Many2one(
        string="Delay Product",
        help="This product will be used to add fines in the Rental Order.",
        comodel_name='product.product',
        related='company_id.extra_product',
        readonly=False,
        domain=[('type', '=', 'service')],
    )

    module_sale_renting_sign = fields.Boolean(string="Digital Documents")

    @api.depends('company_id')
    def _compute_extra_hour(self):
        for setting in self:
            setting.extra_hour = self.env['ir.default']._get(
                'product.template',
                'extra_hourly',
                company_id=setting.company_id.id
            )

    def _inverse_extra_hour(self):
        for setting in self:
            self.env['ir.default'].set(
                'product.template',
                'extra_hourly',
                setting.extra_hour,
                company_id=setting.company_id.id
            )

    @api.depends('company_id')
    def _compute_extra_day(self):
        for setting in self:
            setting.extra_day = self.env['ir.default']._get(
                'product.template',
                'extra_daily',
                company_id=setting.company_id.id
            )

    def _inverse_extra_day(self):
        for setting in self:
            self.env['ir.default'].set(
                'product.template',
                'extra_daily',
                setting.extra_day,
                company_id=setting.company_id.id
            )
