# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class RestaurantFloor(models.Model):
    _name = 'restaurant.floor'

    name = fields.Char(string="Floor Name", required=True, help='An internal identification of the restaurant floor')
    pos_config_id = fields.Many2one('pos.config', string="Point of Sale")
    background_image = fields.Binary(help='A background image used to display a floor layout in the point of sale interface')
    background_color = fields.Char(help='The background color of the floor layout, (must be specified in a html-compatible format)', default="rgb(210, 210, 210)")
    table_ids = fields.One2many('restaurant.table', 'floor_id', string="Tables", help='The list of tables in this floor')
    sequence = fields.Integer(help='Used to sort Floors', default=1)

    @api.one
    def set_background_color(self, background):
        for floor in self:
            floor.write({'background_color': background})

class RestaurantTable(models.Model):
    _name = 'restaurant.table'

    name = fields.Char(string="Table Name", required=True, help='An internal identification of a table')
    floor_id = fields.Many2one('restaurant.floor', string="FLoor")
    shape = fields.Selection([('square', 'Square'), ('round', 'Round')], required=True, default='square')
    position_h = fields.Float(string="Horizontal Position", help="The table's horizontal position from the left side to the table's center, in pixels", default=10)
    position_v = fields.Float(string="Vertical Position", help="The table's vertical position from the top to the table's center, in pixels", default=10)
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
        if table.get('floor_id'):
            floor_id = table['floor_id'][0]
            table['floor_id'] = floor_id

        if table.get('id'):   # Modifiy existing table
            table_id = table['id']
            del table['id']
            self.browse(table_id).write(table)

        else:
            table_id = self.create(table).id
        return table_id

class RestaurantPrinter(models.Model):
    _name = 'restaurant.printer'

    name = fields.Char(string="Printer Name", size=32, required=True, help='An internal identification of the printer', default="Printer")
    proxy_ip = fields.Char(string='Proxy IP Address', size=32, help="The IP Address or hostname of the Printer's hardware proxy")
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
