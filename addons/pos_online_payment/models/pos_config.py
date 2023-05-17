# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    online_payment_provider_ids = fields.Many2many('payment.provider', string="Allowed Providers", help="The online payment providers allowed for paying an order", domain="[('is_published', '=', True), ('state', 'in', ['enabled', 'test'])]")
