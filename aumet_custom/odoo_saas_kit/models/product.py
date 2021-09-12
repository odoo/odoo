# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import api, fields, models

class PrductTemplate(models.Model):
    _inherit = 'product.template'

    saas_plan_id = fields.Many2one(comodel_name="saas.plan", string="SaaS Plan", domain="[('state', '=', 'confirm')]")

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        template_id = vals.get('product_tmpl_id', False)
        if template_id:
            template_obj = self.env['product.template'].browse(template_id)
            vals['recurring_interval'] = template_obj.saas_plan_id and template_obj.saas_plan_id.recurring_interval
            vals['user_cost'] = template_obj.saas_plan_id and template_obj.saas_plan_id.user_cost
        product = super(ProductProduct, self).create(vals)
        return product

    recurring_interval = fields.Integer(string='Billing Cycle/Repeat Every',)
    is_user_pricing = fields.Boolean(string="User pricing", default=False)
    per_user_pricing = fields.Boolean(string="Per User Pricing", related='saas_plan_id.per_user_pricing')
    user_cost = fields.Float(string="User cost", default=1.0)

    @api.onchange('is_user_pricing')
    def check_is_user_pricing(self):
        for obj in self:
            if obj.is_user_pricing:
                obj.saas_plan_id = None

    @api.onchange('saas_plan_id')
    def check_is_saas_plan_id(self):
        for obj in self:
            if obj.saas_plan_id:
                obj.is_user_pricing = False