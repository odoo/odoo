# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RestaurantFloor(models.Model):

    _name = 'restaurant.floor'
    _description = 'Restaurant Floor'

    name = fields.Char('Floor Name', required=True, help='An internal identification of the restaurant floor')
    pos_config_id = fields.Many2one('pos.config', string='Point of Sale')
    background_image = fields.Binary('Background Image', help='A background image used to display a floor layout in the point of sale interface')
    background_color = fields.Char('Background Color', help='The background color of the floor layout, (must be specified in a html-compatible format)', default='rgb(210, 210, 210)')
    table_ids = fields.One2many('restaurant.table', 'floor_id', string='Tables', help='The list of tables in this floor')
    sequence = fields.Integer('Sequence', help='Used to sort Floors', default=1)

    def unlink(self):
        confs = self.mapped('pos_config_id').filtered(lambda c: c.is_table_management == True)
        opened_session = self.env['pos.session'].search([('config_id', 'in', confs.ids), ('state', '!=', 'closed')])
        if opened_session:
            error_msg = _("You cannot remove a floor that is used in a PoS session, close the session(s) first: \n")
            for floor in self:
                for session in opened_session:
                    if floor in session.config_id.floor_ids:
                        error_msg += _("Floor: %s - PoS Config: %s \n") % (floor.name, session.config_id.name)
            if confs:
                raise UserError(error_msg)
        return super(RestaurantFloor, self).unlink()


class RestaurantTable(models.Model):

    _name = 'restaurant.table'
    _description = 'Restaurant Table'

    name = fields.Char('Table Name', required=True, help='An internal identification of a table')
    floor_id = fields.Many2one('restaurant.floor', string='Floor')
    shape = fields.Selection([('square', 'Square'), ('round', 'Round')], string='Shape', required=True, default='square')
    position_h = fields.Float('Horizontal Position', default=10,
        help="The table's horizontal position from the left side to the table's center, in pixels")
    position_v = fields.Float('Vertical Position', default=10,
        help="The table's vertical position from the top to the table's center, in pixels")
    width = fields.Float('Width', default=50, help="The table's width in pixels")
    height = fields.Float('Height', default=50, help="The table's height in pixels")
    seats = fields.Integer('Seats', default=1, help="The default number of customer served at this table.")
    color = fields.Char('Color', help="The table's color, expressed as a valid 'background' CSS property value")
    active = fields.Boolean('Active', default=True, help='If false, the table is deactivated and will not be available in the point of sale')

    @api.model
    def create_from_ui(self, table):
        """ create or modify a table from the point of sale UI.
            table contains the table's fields. If it contains an
            id, it will modify the existing table. It then
            returns the id of the table.
        """
        if table.get('floor_id'):
            table['floor_id'] = table['floor_id'][0]

        table_id = table.pop('id', False)
        if table_id:
            self.browse(table_id).write(table)
        else:
            table_id = self.create(table).id
        return table_id


class RestaurantPrinter(models.Model):

    _name = 'restaurant.printer'
    _description = 'Restaurant Printer'

    name = fields.Char('Printer Name', required=True, default='Printer', help='An internal identification of the printer')
    printer_type = fields.Selection(string='Printer Type', default='iot',
        selection=[('iot', ' Use a printer connected to the IoT Box')])
    proxy_ip = fields.Char('Proxy IP Address', help="The IP Address or hostname of the Printer's hardware proxy")
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
