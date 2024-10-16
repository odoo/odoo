# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        related='partner_id.tenant_code_id',
        readonly=True
    )
    site_code_id = fields.Many2one('site.code.configuration', string='Site Code')
