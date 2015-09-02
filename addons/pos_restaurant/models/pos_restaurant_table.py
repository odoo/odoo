# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RestaurantTable(models.Model):
    _name = 'restaurant.table'

    name = fields.Char(string='Table Name', required=True, help='An internal identification of a table')
    floor_id = fields.Many2one('restaurant.floor', string='Floor')
    shape = fields.Selection([('square', 'Square'), ('round', 'Round')], required=True, default='square')
    position_h = fields.Float(string='Horizontal Position',
                              help="The table's horizontal position from the left side to the table's center, in pixels", default=10)
    position_v = fields.Float(
        string='Vertical Position', help="The table's vertical position from the top to the table's center, in pixels", default=10)
    width = fields.Float(help="The table's width in pixels", default=50)
    height = fields.Float(help="The table's height in pixels", default=50)
    seats = fields.Integer(help="The default number of customer served at this table.", default=1)
    color = fields.Char(help="The table's color, expressed as a valid 'background' CSS property value")
    active = fields.Boolean(help='If false, the table is deactivated and will not be available in the point of sale', default=True)
    pos_order_ids = fields.One2many('pos.order', 'table_id', string='Pos Orders', help='The orders served at this table')

    @api.model
    def create_from_ui(self, table):
        """ create or modify a table from the point of sale UI.
            table contains the table's fields. If it contains an
            id, it will modify the existing table. It then
            returns the id of the table.  """

        if table.get('floor_id', False):
            table['floor_id'] = table['floor_id'][0]

        if table.get('id', False):   # Modifiy existing table
            table_id = table.pop('id')
            self.browse(table_id).write(table)
        else:
            table_id = self.create(table).id
        return table_id
