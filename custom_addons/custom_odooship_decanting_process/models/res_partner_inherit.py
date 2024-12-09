# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    tenant_code_id = fields.Many2one('tenant.code.configuration', string='Tenant Code')