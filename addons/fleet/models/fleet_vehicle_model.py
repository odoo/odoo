# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp import api, fields, models


class FleetVehicleModel(models.Model):

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name, id '

    @api.multi
    def name_get(self):
        return self.mapped(lambda m: (m.id, '/'.join(filter(None, (m.make_id.name, m.name)))))

    name = fields.Char(required=True)
    make_id = fields.Many2one('fleet.make', string='Make', oldname='brand_id', required=True, help='Make of the vehicle')
    vendor_ids = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', oldname='vendors')
    image = fields.Binary(related='make_id.image', string="Logo", store=True)
    image_medium = fields.Binary(related='make_id.image_medium', string="Logo (medium)", store=True)
    image_small = fields.Binary(related='make_id.image_small', string="Logo (small)", store=True)
