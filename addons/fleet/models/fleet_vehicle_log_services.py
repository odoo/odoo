# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp import api, fields, models


class FleetVehicleLogServices(models.Model):

    _name = 'fleet.vehicle.log.services'
    _description = 'Services for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def default_get(self, fields):
        res = super(FleetVehicleLogServices, self).default_get(fields)
        try:
            service_type_id = self.env.ref('fleet.type_service_service_8').id
        except ValueError:
            service_type_id = False
        res.update({'cost_type': 'services', 'cost_subtype_id': service_type_id})
        return res

    purchaser_id = fields.Many2one('res.partner', string='Purchaser',
                                   domain="['|', ('customer', '=', True), ('employee', '=', True)]")
    invoice_reference = fields.Char()
    vendor_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', True)]")
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    # we need to keep this field as a related with store=True because the graph view doesn't support (1) to address
    # fields from inherited table and (2) fields that aren't stored in database
    notes = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    date = fields.Date(default=fields.Date.context_today)

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.odometer_unit = self.vehicle_id.odometer_unit
        self.purchaser_id = self.vehicle_id.driver_id
