# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import time
import datetime
from openerp import tools
from openerp.exceptions import UserError
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta

def str_to_datetime(strdate):
    return datetime.datetime.strptime(strdate, tools.DEFAULT_SERVER_DATE_FORMAT)

class fleet_vehicle_cost(osv.Model):
    _name = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle'
    _order = 'date desc, vehicle_id asc'

    def _get_odometer(self, cr, uid, ids, odometer_id, arg, context):
        res = dict.fromkeys(ids, False)
        for record in self.browse(cr,uid,ids,context=context):
            if record.odometer_id:
                res[record.id] = record.odometer_id.value
        return res

    def _set_odometer(self, cr, uid, id, name, value, args=None, context=None):
        if not value:
            raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
        date = self.browse(cr, uid, id, context=context).date
        if not(date):
            date = fields.date.context_today(self, cr, uid, context=context)
        vehicle_id = self.browse(cr, uid, id, context=context).vehicle_id
        data = {'value': value, 'date': date, 'vehicle_id': vehicle_id.id}
        odometer_id = self.pool.get('fleet.vehicle.odometer').create(cr, uid, data, context=context)
        return self.write(cr, uid, id, {'odometer_id': odometer_id}, context=context)

    _columns = {
        'name': fields.related('vehicle_id', 'name', type="char", string='Name', store=True),
        'vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle', required=True, help='Vehicle concerned by this log'),
        'cost_subtype_id': fields.many2one('fleet.service.type', 'Type', help='Cost type purchased with this cost'),
        'amount': fields.float('Total Price'),
        'cost_type': fields.selection([('contract', 'Contract'), ('services','Services'), ('fuel','Fuel'), ('other','Other')], 'Category of the cost', help='For internal purpose only', required=True),
        'parent_id': fields.many2one('fleet.vehicle.cost', 'Parent', help='Parent cost to this current cost'),
        'cost_ids': fields.one2many('fleet.vehicle.cost', 'parent_id', 'Included Services'),
        'odometer_id': fields.many2one('fleet.vehicle.odometer', 'Odometer', help='Odometer measure of the vehicle at the moment of this log'),
        'odometer': fields.function(_get_odometer, fnct_inv=_set_odometer, type='float', string='Odometer Value', help='Odometer measure of the vehicle at the moment of this log'),
        'odometer_unit': fields.related('vehicle_id', 'odometer_unit', type="char", string="Unit", readonly=True),
        'date' :fields.date('Date',help='Date when the cost has been executed'),
        'contract_id': fields.many2one('fleet.vehicle.log.contract', 'Contract', help='Contract attached to this cost'),
        'auto_generated': fields.boolean('Automatically Generated', readonly=True),
    }

    _defaults ={
        'cost_type': 'other',
    }

    def create(self, cr, uid, data, context=None):
        #make sure that the data are consistent with values of parent and contract records given
        if 'parent_id' in data and data['parent_id']:
            parent = self.browse(cr, uid, data['parent_id'], context=context)
            data['vehicle_id'] = parent.vehicle_id.id
            data['date'] = parent.date
            data['cost_type'] = parent.cost_type
        if 'contract_id' in data and data['contract_id']:
            contract = self.pool.get('fleet.vehicle.log.contract').browse(cr, uid, data['contract_id'], context=context)
            data['vehicle_id'] = contract.vehicle_id.id
            data['cost_subtype_id'] = contract.cost_subtype_id.id
            data['cost_type'] = contract.cost_type
        if 'odometer' in data and not data['odometer']:
            #if received value for odometer is 0, then remove it from the data as it would result to the creation of a
            #odometer log with 0, which is to be avoided
            del(data['odometer'])
        return super(fleet_vehicle_cost, self).create(cr, uid, data, context=context)






