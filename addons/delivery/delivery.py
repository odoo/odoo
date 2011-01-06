# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import netsvc
from osv import fields,osv
from tools.translate import _
from tools.safe_eval import safe_eval

class delivery_carrier(osv.osv):
    _name = "delivery.carrier"
    _description = "Carrier and delivery grids"

    def get_price(self, cr, uid, ids, field_name, arg=None, context={}):
        res={}
        sale_obj=self.pool.get('sale.order')
        grid_obj=self.pool.get('delivery.grid')
        for carrier in self.browse(cr,uid,ids,context):
            order_id=context.get('order_id',False)
            price=False
            if order_id:
              order = sale_obj.browse(cr, uid, [order_id])[0]
              carrier_grid=self.grid_get(cr,uid,[carrier.id],order.partner_shipping_id.id,context)
              if carrier_grid:
                  price=grid_obj.get_price(cr, uid, carrier_grid, order, time.strftime('%Y-%m-%d'), context)
              else:
                  price = 0.0
            res[carrier.id]=price
        return res
    _columns = {
        'name': fields.char('Carrier', size=64, required=True),
        'partner_id': fields.many2one('res.partner', 'Carrier Partner', required=True),
        'product_id': fields.many2one('product.product', 'Delivery Product', required=True),
        'grids_id': fields.one2many('delivery.grid', 'carrier_id', 'Delivery Grids'),
        'price' : fields.function(get_price, method=True,string='Price'),
        'active': fields.boolean('Active')
    }
    _defaults = {
        'active': lambda *args:1
    }
    def grid_get(self, cr, uid, ids, contact_id, context={}):
        contact = self.pool.get('res.partner.address').browse(cr, uid, [contact_id])[0]
        for carrier in self.browse(cr, uid, ids):
            for grid in carrier.grids_id:
                get_id = lambda x: x.id
                country_ids = map(get_id, grid.country_ids)
                state_ids = map(get_id, grid.state_ids)
                if country_ids and not contact.country_id.id in country_ids:
                    continue
                if state_ids and not contact.state_id.id in state_ids:
                    continue
                if grid.zip_from and (contact.zip or '')< grid.zip_from:
                    continue
                if grid.zip_to and (contact.zip or '')> grid.zip_to:
                    continue
                return grid.id
        return False
delivery_carrier()

class delivery_grid(osv.osv):
    _name = "delivery.grid"
    _description = "Delivery Grid"
    _columns = {
        'name': fields.char('Grid Name', size=64, required=True),
        'sequence': fields.integer('Sequence', size=64, required=True),
        'carrier_id': fields.many2one('delivery.carrier', 'Carrier', required=True, ondelete='cascade'),
        'country_ids': fields.many2many('res.country', 'delivery_grid_country_rel', 'grid_id', 'country_id', 'Countries'),
        'state_ids': fields.many2many('res.country.state', 'delivery_grid_state_rel', 'grid_id', 'state_id', 'States'),
        'zip_from': fields.char('Start Zip', size=12),
        'zip_to': fields.char('To Zip', size=12),
        'line_ids': fields.one2many('delivery.grid.line', 'grid_id', 'Grid Line'),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *a: 1,
        'sequence': lambda *a: 1,
    }
    _order = 'sequence'


    def get_price(self, cr, uid, id, order, dt, context):

        total = 0
        weight = 0
        volume = 0
        for line in order.order_line:
            if not line.product_id:
                continue
            total += line.price_subtotal or 0.0
            weight += (line.product_id.weight or 0.0) * line.product_uom_qty
            volume += (line.product_id.volume or 0.0) * line.product_uom_qty


        return self.get_price_from_picking(cr, uid, id, total,weight, volume, context)

    def get_price_from_picking(self, cr, uid, id, total, weight, volume, context={}):
        grid = self.browse(cr, uid, id, context)

        price = 0.0
        ok = False

        for line in grid.line_ids:
            price_dict = {'price': total, 'volume':volume, 'weight': weight, 'wv':volume*weight}
            test = safe_eval(line.type+line.operator+str(line.max_value), price_dict)
            if test:
                if line.price_type=='variable':
                    price = line.list_price * price_dict[line.variable_factor]
                else:
                    price = line.list_price
                ok = True
                break
        if not ok:
            raise osv.except_osv(_('No price available !'), _('No line matched this order in the choosed delivery grids !'))

        return price


delivery_grid()

class delivery_grid_line(osv.osv):
    _name = "delivery.grid.line"
    _description = "Delivery line of grid"
    _columns = {
        'name': fields.char('Name', size=32, required=True),
        'grid_id': fields.many2one('delivery.grid', 'Grid',required=True),
        'type': fields.selection([('weight','Weight'),('volume','Volume'),('wv','Weight * Volume'), ('price','Price')], 'Variable', required=True),
        'operator': fields.selection([('=','='),('<=','<='),('>=','>=')], 'Operator', required=True),
        'max_value': fields.float('Maximum Value', required=True),
        'price_type': fields.selection([('fixed','Fixed'),('variable','Variable')], 'Price Type', required=True),
        'variable_factor': fields.selection([('weight','Weight'),('volume','Volume'),('wv','Weight * Volume'), ('price','Price')], 'Variable Factor', required=True),
        'list_price': fields.float('Sale Price', required=True),
        'standard_price': fields.float('Cost Price', required=True),
    }
    _defaults = {
        'type': lambda *args: 'weight',
        'operator': lambda *args: '<=',
        'price_type': lambda *args: 'fixed',
        'variable_factor': lambda *args: 'weight',
    }
    _order = 'list_price'


delivery_grid_line()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

