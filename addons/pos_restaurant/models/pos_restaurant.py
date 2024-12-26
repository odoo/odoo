# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class RestaurantFloor(models.Model):
    _name = 'restaurant.floor'

    _description = 'Restaurant Floor'
    _order = "sequence, name"
    _inherit = ['pos.load.mixin']

    name = fields.Char('Floor Name', required=True)
    pos_config_ids = fields.Many2many('pos.config', string='Point of Sales', domain="[('module_pos_restaurant', '=', True)]")
    background_image = fields.Binary('Background Image')
    background_color = fields.Char('Background Color', help='The background color of the floor in a html-compatible format', default='rgb(249,250,251)')
    table_ids = fields.One2many('restaurant.table', 'floor_id', string='Tables')
    sequence = fields.Integer('Sequence', default=1)
    active = fields.Boolean(default=True)
    floor_background_image = fields.Image(string='Floor Background Image')
    floor_prefix = fields.Integer('Floor Prefix', default=1, help="The prefix will be used when creating a new table in the PoS interface.")

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_config_ids', '=', data['pos.config'][0]['id'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name', 'background_color', 'table_ids', 'sequence', 'pos_config_ids', 'floor_background_image', 'floor_prefix']

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        confs = self.mapped('pos_config_ids').filtered(lambda c: c.module_pos_restaurant)
        opened_session = self.env['pos.session'].search([('config_id', 'in', confs.ids), ('state', '!=', 'closed')])
        if opened_session and confs:
            error_msg = _("You cannot remove a floor that is used in a PoS session, close the session(s) first: \n")
            for floor in self:
                for session in opened_session:
                    if floor in session.config_id.floor_ids:
                        error_msg += _("Floor: %(floor)s - PoS Config: %(config)s \n", floor=floor.name, config=session.config_id.name)
            raise UserError(error_msg)

    def write(self, vals):
        for floor in self:
            for config in floor.pos_config_ids:
                if config.has_active_session and (vals.get('pos_config_ids') or vals.get('active')):
                    raise UserError(
                        self.env._(
                            "Please close and validate the following open PoS Session before modifying this floor.\n"
                            "Open session: %(session_names)s",
                            session_names=" ".join(config.mapped("name")),
                        )
                    )
            for table in floor.table_ids:
                # Verify if table number begin by old prefix if it is not 0
                if (self.floor_prefix == 0 or (table.table_number and str(table.table_number).startswith(str(self.floor_prefix)))) and vals.get('floor_prefix') is not None:
                    table_number_wo_prefix = str(table.table_number)[len(str(self.floor_prefix)):] if self.floor_prefix != 0 else str(table.table_number).zfill(2)
                    table.table_number = str(vals.get('floor_prefix')) + table_number_wo_prefix

        return super().write(vals)

    def rename_floor(self, new_name):
        for floor in self:
            floor.name = new_name

    @api.model
    def sync_from_ui(self, name, background_color, config_id):
        floor_fields = {
            "name": name,
            "background_color": background_color,
        }
        pos_floor = self.create(floor_fields)
        pos_floor.pos_config_ids = [Command.link(config_id)]
        return {
            'id': pos_floor.id,
            'name': pos_floor.name,
            'background_color': pos_floor.background_color,
            'table_ids': [],
            'sequence': pos_floor.sequence,
            'tables': [],
        }

    def deactivate_floor(self, session_id):
        draft_orders = self.env['pos.order'].search([('session_id', '=', session_id), ('state', '=', 'draft'), ('table_id.floor_id', '=', self.id)])
        if draft_orders:
            raise UserError(_("You cannot delete a floor when orders are still in draft for this floor."))
        for table in self.table_ids:
            table.active = False
        self.active = False

        return True


class RestaurantTable(models.Model):
    _name = 'restaurant.table'

    _description = 'Restaurant Table'
    _inherit = ['pos.load.mixin']

    floor_id = fields.Many2one('restaurant.floor', string='Floor')
    table_number = fields.Integer('Table Number', required=True, help='The number of the table as displayed on the floor plan', default=0)
    shape = fields.Selection([('square', 'Square'), ('round', 'Round')], string='Shape', required=True, default='square')
    position_h = fields.Float('Horizontal Position', default=10,
        help="The table's horizontal position from the left side to the table's center, in pixels")
    position_v = fields.Float('Vertical Position', default=10,
        help="The table's vertical position from the top to the table's center, in pixels")
    width = fields.Float('Width', default=50, help="The table's width in pixels")
    height = fields.Float('Height', default=50, help="The table's height in pixels")
    seats = fields.Integer('Seats', default=1, help="The default number of customer served at this table.")
    color = fields.Char('Color', help="The table's color, expressed as a valid 'background' CSS property value", default="#35D374")
    parent_id = fields.Many2one('restaurant.table', string='Parent Table', help="The parent table if this table is part of a group of tables")
    active = fields.Boolean('Active', default=True, help='If false, the table is deactivated and will not be available in the point of sale')

    @api.depends('table_number', 'floor_id')
    def _compute_display_name(self):
        for table in self:
            table.display_name = f"{table.floor_id.name}, {table.table_number}"

    @api.model
    def _load_pos_data_domain(self, data):
        floor_ids = self.env['pos.config'].browse(data['pos.config'][0]['id']).floor_ids.ids
        return [('active', '=', True), ('floor_id', 'in', floor_ids)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['table_number', 'width', 'height', 'position_h', 'position_v', 'parent_id', 'shape', 'floor_id', 'color', 'seats', 'active']

    def are_orders_still_in_draft(self):
        draft_orders_count = self.env['pos.order'].search_count([('table_id', 'in', self.ids), ('state', '=', 'draft')])

        if draft_orders_count > 0:
            raise UserError(_("You cannot delete a table when orders are still in draft for this table."))

        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        confs = self.mapped('floor_id.pos_config_ids').filtered(lambda c: c.module_pos_restaurant)
        opened_session = self.env['pos.session'].search([('config_id', 'in', confs.ids), ('state', '!=', 'closed')])
        if opened_session:
            error_msg = _("You cannot remove a table that is used in a PoS session, close the session(s) first.")
            if confs:
                raise UserError(error_msg)

    def update_tables(self, tables_by_id):
        for table in self:
            table.write(tables_by_id[str(table.id)])
