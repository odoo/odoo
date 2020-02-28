# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    is_service = fields.Boolean('Is a service', compute='_compute_is_service',
                                help="Should generate a projet/task if product\
                                is a service depending on his configuration")
    
    @api.depends('product_id')
    def _compute_is_service(self):
        for line in self:
            if line.product_id.type == 'service':
                line.is_service = True
            else:
                line.is_service = False
