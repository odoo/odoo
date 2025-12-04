# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from base64 import b64decode

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

FLOOR_PLAN_SUPPORTED_IMAGE_MIMETYPES = {
    'image/gif': '.gif',
    'image/jpe': '.jpe',
    'image/jpeg': '.jpeg',
    'image/jpg': '.jpg',
    'image/png': '.png',
    'image/svg+xml': '.svg',
    'image/webp': '.webp',
}


class RestaurantFloor(models.Model):
    _name = 'restaurant.floor'

    _description = 'Restaurant Floor'
    _order = "sequence, name"
    _inherit = ['pos.load.mixin']

    name = fields.Char('Floor Name', required=True)
    pos_config_ids = fields.Many2many('pos.config', string='Point of Sales', domain="[('module_pos_restaurant', '=', True)]")
    table_ids = fields.One2many('restaurant.table', 'floor_id', string='Tables')
    sequence = fields.Integer('Sequence', default=1)
    active = fields.Boolean(default=True)
    floor_plan_layout = fields.Json(string='Floor Plan Layout')

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('pos_config_ids', '=', config.id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'table_ids', 'sequence', 'pos_config_ids']

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

        return super().write(vals)

    def deactivate_floor(self, session_id):
        draft_orders = self.env['pos.order'].search([('session_id', '=', session_id), ('state', '=', 'draft'), ('table_id.floor_id', '=', self.id)])
        if draft_orders:
            raise UserError(_("You cannot delete a floor when orders are still in draft for this floor."))
        for table in self.table_ids:
            table.active = False
        self.active = False

        return True

    @api.model
    def add_floor_plan_image(self, name, data):
        img = b64decode(data)
        mimetype = guess_mimetype(img)
        if mimetype not in FLOOR_PLAN_SUPPORTED_IMAGE_MIMETYPES:
            raise UserError(_("Uploaded image's format is not supported. Try with: %s", ', '.join(FLOOR_PLAN_SUPPORTED_IMAGE_MIMETYPES.values())))
        IrAttachment = self.env['ir.attachment']
        checksum = IrAttachment._compute_checksum(img)
        if not name:
            name = f"{str(uuid.uuid4())[:6]}{FLOOR_PLAN_SUPPORTED_IMAGE_MIMETYPES[mimetype]}"
        attachment_data = {
            'name': name,
            'res_model': 'restaurant.floor',
            'res_id': 0,  # linked later
        }
        domain = [(field, '=', value) for field, value in attachment_data.items()]
        domain.append(('checksum', '=', checksum))
        attachment = IrAttachment.search(domain, limit=1) or None
        if not attachment:
            attachment_data['raw'] = img
            attachment = IrAttachment.create(attachment_data)
        return {'id': attachment.id, 'url': attachment.image_src}

    @api.autovacuum
    def _gc_embeddings(self):
        """
        Autovacuum: Cleanup floor plan images not associated
        """
        self.env['ir.attachment'].search([
            ('res_model', '=', 'restaurant.floor'),
            ('res_field', '=', False),
            ('res_id', '=', 0),
            ('write_date', '<', fields.Datetime.now() - relativedelta(days=1))
        ]).unlink()


class RestaurantTable(models.Model):
    _name = 'restaurant.table'

    _description = 'Restaurant Table'
    _inherit = ['pos.load.mixin']

    floor_id = fields.Many2one('restaurant.floor', string='Floor', index='btree_not_null')
    table_number = fields.Integer('Table Number', required=True, help='The number of the table as displayed on the floor plan', default=0)
    seats = fields.Integer('Seats', default=1, help="The default number of customer served at this table.")
    parent_id = fields.Many2one('restaurant.table', string='Parent Table', help="The parent table if this table is part of a group of tables")
    parent_side = fields.Selection(string='Parent Side', selection=[('left', 'Left'), ('right', 'Right'), ('top', 'Top'), ('bottom', 'Bottom')], help="The parent table side where this table will be displayed")
    active = fields.Boolean('Active', default=True, help='If false, the table is deactivated and will not be available in the point of sale')
    floor_plan_layout = fields.Json(string='Floor Plan Layout')

    @api.depends('table_number', 'floor_id')
    def _compute_display_name(self):
        for table in self:
            table.display_name = f"{table.floor_id.name}, {table.table_number}"

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('active', '=', True), ('floor_id', 'in', config.floor_ids.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['table_number', 'parent_id', 'parent_side', 'floor_id', 'seats', 'active']

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
