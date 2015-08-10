# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class fleet_vehicle_log_fuel(osv.Model):

    def on_change_vehicle(self, cr, uid, ids, vehicle_id, context=None):
        if not vehicle_id:
            return {}
        vehicle = self.pool.get('fleet.vehicle').browse(cr, uid, vehicle_id, context=context)
        odometer_unit = vehicle.odometer_unit
        driver = vehicle.driver_id.id
        return {
            'value': {
                'odometer_unit': odometer_unit,
                'purchaser_id': driver,
            }
        }

    def on_change_liter(self, cr, uid, ids, liter, price_per_liter, amount, context=None):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        liter = float(liter)
        price_per_liter = float(price_per_liter)
        amount = float(amount)
        if liter > 0 and price_per_liter > 0 and round(liter*price_per_liter,2) != amount:
            return {'value' : {'amount' : round(liter * price_per_liter,2),}}
        elif amount > 0 and liter > 0 and round(amount/liter,2) != price_per_liter:
            return {'value' : {'price_per_liter' : round(amount / liter,2),}}
        elif amount > 0 and price_per_liter > 0 and round(amount/price_per_liter,2) != liter:
            return {'value' : {'liter' : round(amount / price_per_liter,2),}}
        else :
            return {}

    def on_change_price_per_liter(self, cr, uid, ids, liter, price_per_liter, amount, context=None):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        liter = float(liter)
        price_per_liter = float(price_per_liter)
        amount = float(amount)
        if liter > 0 and price_per_liter > 0 and round(liter*price_per_liter,2) != amount:
            return {'value' : {'amount' : round(liter * price_per_liter,2),}}
        elif amount > 0 and price_per_liter > 0 and round(amount/price_per_liter,2) != liter:
            return {'value' : {'liter' : round(amount / price_per_liter,2),}}
        elif amount > 0 and liter > 0 and round(amount/liter,2) != price_per_liter:
            return {'value' : {'price_per_liter' : round(amount / liter,2),}}
        else :
            return {}

    def on_change_amount(self, cr, uid, ids, liter, price_per_liter, amount, context=None):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        liter = float(liter)
        price_per_liter = float(price_per_liter)
        amount = float(amount)
        if amount > 0 and liter > 0 and round(amount/liter,2) != price_per_liter:
            return {'value': {'price_per_liter': round(amount / liter,2),}}
        elif amount > 0 and price_per_liter > 0 and round(amount/price_per_liter,2) != liter:
            return {'value': {'liter': round(amount / price_per_liter,2),}}
        elif liter > 0 and price_per_liter > 0 and round(liter*price_per_liter,2) != amount:
            return {'value': {'amount': round(liter * price_per_liter,2),}}
        else :
            return {}

    def _get_default_service_type(self, cr, uid, context):
        try:
            model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'fleet', 'type_service_refueling')
        except ValueError:
            model_id = False
        return model_id

    _name = 'fleet.vehicle.log.fuel'
    _description = 'Fuel log for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    _columns = {
        'liter': fields.float('Liter'),
        'price_per_liter': fields.float('Price Per Liter'),
        'purchaser_id': fields.many2one('res.partner', 'Purchaser', domain="['|',('customer','=',True),('employee','=',True)]"),
        'inv_ref': fields.char('Invoice Reference', size=64),
        'vendor_id': fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]"),
        'notes': fields.text('Notes'),
        'cost_id': fields.many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade'),
        'cost_amount': fields.related('cost_id', 'amount', string='Amount', type='float', store=True), #we need to keep this field as a related with store=True because the graph view doesn't support (1) to address fields from inherited table and (2) fields that aren't stored in database
    }
    _defaults = {
        'date': fields.date.context_today,
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'fuel',
    }
