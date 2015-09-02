# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RestaurantFloor(models.Model):
    _name = 'restaurant.floor'

    name = fields.Char(string='Floor Name', required=True, help='An internal identification of the restaurant floor')
    pos_config_id = fields.Many2one('pos.config', string='Point of Sale')
    background_image = fields.Binary(string='Background Image', attachment=True, help='A background image used to display a floor layout in the point of sale interface')
    background_color = fields.Char(string='Background Color', help='The background color of the floor layout, (must be specified in a html-compatible format)', default='rgb(210, 210, 210)')
    table_ids = fields.One2many('restaurant.table', 'floor_id', string='Tables', help='The list of tables in this floor')
    sequence = fields.Integer(help='Used to sort Floors', default=1)

    @api.multi
    def set_background_color(self, background):
        return self.write({'background_color': background})
