# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
# TODO: make it so you can start typing the name of the link w\o having to click on the 'NEW' button first
class PosSelfOrderCustomLink(models.Model):
    _name = 'pos_self_order.custom_link'
    _description = 'Custom links that the restaurant can configure to be displayed on the self order screen'
    url =  fields.Char(string='URL', required=True)
    name = fields.Char(string='Label', required=True, translate=True)
    pos_config_id = fields.Many2many('pos.config', string='Point of Sale')
    style = fields.Selection([('primary', 'Primary'), 
                              ('secondary', 'Secondary'),
                              ('success', 'Success'),
                              ('warning', 'Warning'), 
                              ('danger', 'Danger'),
                              ('info', 'Info'), 
                              ('light', 'Light'), 
                              ('dark', 'Dark'),
                            ],      
            string='Style', default='primary')
    sequence = fields.Integer('Sequence', default=1)

    