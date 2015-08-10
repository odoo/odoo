# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import time
import datetime
from openerp import tools
from openerp.exceptions import UserError
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta


class fleet_vehicle_model(osv.Model):

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.brand_id.name:
                name = record.brand_id.name + '/' + name
            res.append((record.id, name))
        return res

    def on_change_brand(self, cr, uid, ids, model_id, context=None):
        if not model_id:
            return {'value': {'image_medium': False}}
        brand = self.pool.get('fleet.vehicle.model.brand').browse(cr, uid, model_id, context=context)
        return {
            'value': {
                'image_medium': brand.image,
            }
        }

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc'

    _columns = {
        'name': fields.char('Model name', required=True),
        'brand_id': fields.many2one('fleet.vehicle.model.brand', 'Make', required=True, help='Make of the vehicle'),
        'vendors': fields.many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors'),
        'image': fields.related('brand_id', 'image', type="binary", string="Logo"),
        'image_medium': fields.related('brand_id', 'image_medium', type="binary", string="Logo (medium)"),
        'image_small': fields.related('brand_id', 'image_small', type="binary", string="Logo (small)"),
    }
