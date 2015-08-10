# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class FleetVehicleLogFuel(models.Model):

    _name = 'fleet.vehicle.log.fuel'
    _description = 'Fuel log for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def default_get(self, fields):
        res = super(FleetVehicleLogFuel, self).default_get(fields)
        try:
            service_type_id = self.env.ref('fleet.type_service_refueling').id
        except ValueError:
            service_type_id = False
        res.update({'cost_type': 'fuel', 'cost_subtype_id': service_type_id})
        return res

    liter = fields.Float()
    price_per_liter = fields.Float()
    purchaser_id = fields.Many2one('res.partner', string='Purchaser',
                                   domain="['|', ('customer', '=', True), ('employee', '=', True)]")
    invoice_reference = fields.Char()
    vendor_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', True)]")
    notes = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    date = fields.Date(default=fields.Date.context_today)
    # we need to keep this field as a related with store=True because the graph view doesn't support (1) to address
    # fields from inherited table and (2) fields that aren't stored in database

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.odometer_unit = self.vehicle_id.odometer_unit
        self.purchaser_id = self.vehicle_id.driver_id

    @api.onchange('liter', 'price_per_liter', 'amount')
    def on_change_liter(self):
        """
        need to cast in float because the value received from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = self.liter
        price_per_liter = self.price_per_liter
        amount = self.amount
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)

    @api.onchange('price_per_liter')
    def on_change_price_per_liter(self):
        """
        need to cast in float because the value received from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = self.liter
        price_per_liter = self.price_per_liter
        amount = self.amount
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)

    @api.onchange('amount')
    def on_change_amount(self):
        """
        need to cast in float because the value received from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = self.liter
        price_per_liter = self.price_per_liter
        amount = self.amount
        if amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)
        elif liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
