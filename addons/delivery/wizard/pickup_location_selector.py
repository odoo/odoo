# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PickupLocationSelector(models.TransientModel):
    _name = 'pickup.location.selector'
    _description = 'Pickup Location Selector'

    parent_model = fields.Char(required=True)
    parent_id = fields.Integer(required=True)
    zip_code = fields.Char()
    selected_pickup_location = fields.Char(compute='_compute_selected_pickup_location')

    @api.depends('parent_model', 'parent_id')
    def _compute_selected_pickup_location(self):
        for wizard in self:
            parent = wizard._parent_record()
            location_data = parent[parent._get_pickup_point_address_field_name()].location_data
            wizard.selected_pickup_location = location_data.get('id', False) if location_data else False

    def _parent_record(self):
        self.ensure_one()
        return self.env[self.parent_model].browse(self.parent_id)
