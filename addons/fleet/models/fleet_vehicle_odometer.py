# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class fleet_vehicle_odometer(osv.Model):
    _name='fleet.vehicle.odometer'
    _description='Odometer log for a vehicle'
    _order='date desc'

    def _vehicle_log_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            name = record.vehicle_id.name
            if not name:
                name = record.date
            elif record.date:
                name += ' / '+ record.date
            res[record.id] = name
        return res

    def on_change_vehicle(self, cr, uid, ids, vehicle_id, context=None):
        if not vehicle_id:
            return {}
        odometer_unit = self.pool.get('fleet.vehicle').browse(cr, uid, vehicle_id, context=context).odometer_unit
        return {
            'value': {
                'unit': odometer_unit,
            }
        }

    _columns = {
        'name': fields.function(_vehicle_log_name_get_fnc, type="char", string='Name', store=True),
        'date': fields.date('Date'),
        'value': fields.float('Odometer Value', group_operator="max"),
        'vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle', required=True),
        'unit': fields.related('vehicle_id', 'odometer_unit', type="char", string="Unit", readonly=True),
    }
    _defaults = {
        'date': fields.date.context_today,
    }
