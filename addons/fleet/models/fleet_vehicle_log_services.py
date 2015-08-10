# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import time
import datetime
from openerp import tools
from openerp.exceptions import UserError
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta

class fleet_vehicle_log_services(osv.Model):

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

    def _get_default_service_type(self, cr, uid, context):
        try:
            model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'fleet', 'type_service_service_8')
        except ValueError:
            model_id = False
        return model_id

    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _name = 'fleet.vehicle.log.services'
    _description = 'Services for vehicles'
    _columns = {
        'purchaser_id': fields.many2one('res.partner', 'Purchaser', domain="['|',('customer','=',True),('employee','=',True)]"),
        'inv_ref': fields.char('Invoice Reference'),
        'vendor_id': fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]"),
        'cost_amount': fields.related('cost_id', 'amount', string='Amount', type='float', store=True), #we need to keep this field as a related with store=True because the graph view doesn't support (1) to address fields from inherited table and (2) fields that aren't stored in database
        'notes': fields.text('Notes'),
        'cost_id': fields.many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade'),
    }
    _defaults = {
        'date': fields.date.context_today,
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'services'
    }
