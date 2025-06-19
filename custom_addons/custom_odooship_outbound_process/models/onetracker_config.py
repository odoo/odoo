# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class OneTrakerMerchantConfig(models.Model):
    _name = 'onetracker.connection.config'
    _description = 'OneTraker connection Configuration'
    _rec_name = 'name'
    _sql_constraints = [
        ('unique_onetracker_name', 'unique(name)', 'The configuration name must be unique.')
    ]

    name = fields.Char(string="Merchant Name", required=True)
    merchant_code = fields.Char(string="Merchant Code", required=True)
    site_code_id = fields.Many2one('site.code.configuration', string='Site Code', required=True)
    tenant_code_id = fields.Many2one('tenant.code.configuration', string='Tenant Code', required=True)

    onetraker_order_url = fields.Char(string="ONETRAKER_CREATE_ORDER_URL", required=True)
    default_from_location_id = fields.Char(string="DEFAULT_FROM_LOCATION_ID", required=True)
    default_auto_generate_label = fields.Boolean(string="DEFAULT_AUTO_GENERATE_LABEL", default=True)
    bearer_token = fields.Text(string="BEARER", required=True)
    is_production = fields.Boolean(string="Is Production Environment", default=False)

