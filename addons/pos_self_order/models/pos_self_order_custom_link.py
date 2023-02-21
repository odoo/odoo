# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosSelfOrderCustomLink(models.Model):
    _name = 'pos_self_order.custom_link'
    _description = 'Custom links that the restaurant can configure to be displayed on the self order screen'
    url =  fields.Char(string='URL', required=True)
    name = fields.Char(string='Label', required=True)
    pos_config_id = fields.Many2many('pos.config', string='Pos Config')

    