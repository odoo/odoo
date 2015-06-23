# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import fields,osv
from openerp.tools.translate import _


class delivery_carrier(osv.osv):
    _name = "delivery.carrier"
    _description = "Carrier"
    _order = 'sequence, id'

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        if context is None:
            context = {}
        order_id = context.get('order_id',False)
        if not order_id:
            res = super(delivery_carrier, self).name_get(cr, uid, ids, context=context)
        else:
            order = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)
            currency = order.pricelist_id.currency_id.name or ''
            res = [(r['id'], r['name']+' ('+(str(r['price']))+' '+currency+')') for r in self.read(cr, uid, ids, ['name', 'price'], context)]
        return res

    def get_price(self, cr, uid, ids, field_name, arg=None, context=None):
        res={}
        if context is None:
            context = {}
        sale_obj=self.pool.get('sale.order')
        grid_obj=self.pool.get('delivery.grid')
        for carrier in self.browse(cr, uid, ids, context=context):
            order_id=context.get('order_id',False)
            price=False
            available = False
            if order_id:
              order = sale_obj.browse(cr, uid, order_id, context=context)
              carrier_grid=self.grid_get(cr,uid,[carrier.id],order.partner_shipping_id.id,context)
              if carrier_grid:
                  try:
                    price=grid_obj.get_price(cr, uid, carrier_grid, order, time.strftime('%Y-%m-%d'), context)
                    available = True
                  except UserError, e:
                    # no suitable delivery method found, probably configuration error
                    _logger.info("Carrier %s: %s", carrier.name, e.name)
                    price = 0.0
              else:
                  price = 0.0
            res[carrier.id] = {
                'price': price,
                'available': available
            }
        return res

    _columns = {
        'name': fields.char('Delivery Method', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Determine the display order"),
        'partner_id': fields.many2one('res.partner', 'Transport Company', required=True, help="The partner that is doing the delivery service."),
        'product_id': fields.many2one('product.product', 'Delivery Product', required=True),
        'grids_id': fields.one2many('delivery.grid', 'carrier_id', 'Delivery Grids'),
        'available' : fields.function(get_price, string='Available',type='boolean', multi='price',
            help="Is the carrier method possible with the current order."),
        'price' : fields.function(get_price, string='Price', multi='price'),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the delivery carrier without removing it."),
        'normal_price': fields.float('Normal Price', help="Keep empty if the pricing depends on the advanced pricing per destination"),
        'free_if_more_than': fields.boolean('Free If Order Total Amount Is More Than', help="If the order is more expensive than a certain amount, the customer can benefit from a free shipping"),
        'amount': fields.float('Amount', help="Amount of the order to benefit from a free shipping, expressed in the company currency"),
        'use_detailed_pricelist': fields.boolean('Advanced Pricing per Destination', help="Check this box if you want to manage delivery prices that depends on the destination, the weight, the total of the order, etc."),
        'pricelist_ids': fields.one2many('delivery.grid', 'carrier_id', 'Advanced Pricing'),
    }

    _defaults = {
        'active': 1,
        'free_if_more_than': False,
        'sequence': 10,
    }

    def grid_get(self, cr, uid, ids, contact_id, context=None):
        contact = self.pool.get('res.partner').browse(cr, uid, contact_id, context=context)
        for carrier in self.browse(cr, uid, ids, context=context):
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

    def create_grid_lines(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        grid_line_pool = self.pool.get('delivery.grid.line')
        grid_pool = self.pool.get('delivery.grid')
        for record in self.browse(cr, uid, ids, context=context):
            # if using advanced pricing per destination: do not change
            if record.use_detailed_pricelist:
                continue

            # not using advanced pricing per destination: override grid
            grid_id = grid_pool.search(cr, uid, [('carrier_id', '=', record.id)], context=context)
            if grid_id and not (record.normal_price or record.free_if_more_than):
                grid_pool.unlink(cr, uid, grid_id, context=context)
                grid_id = None

            # Check that float, else 0.0 is False
            if not (isinstance(record.normal_price,float) or record.free_if_more_than):
                continue

            if not grid_id:
                grid_data = {
                    'name': record.name,
                    'carrier_id': record.id,
                    'sequence': 10,
                }
                grid_id = [grid_pool.create(cr, uid, grid_data, context=context)]

            lines = grid_line_pool.search(cr, uid, [('grid_id','in',grid_id)], context=context)
            if lines:
                grid_line_pool.unlink(cr, uid, lines, context=context)

            #create the grid lines
            if record.free_if_more_than:
                line_data = {
                    'grid_id': grid_id and grid_id[0],
                    'name': _('Free if more than %.2f') % record.amount,
                    'type': 'price',
                    'operator': '>=',
                    'max_value': record.amount,
                    'standard_price': 0.0,
                    'list_price': 0.0,
                }
                grid_line_pool.create(cr, uid, line_data, context=context)
            if isinstance(record.normal_price,float):
                line_data = {
                    'grid_id': grid_id and grid_id[0],
                    'name': _('Default price'),
                    'type': 'price',
                    'operator': '>=',
                    'max_value': 0.0,
                    'standard_price': record.normal_price,
                    'list_price': record.normal_price,
                }
                grid_line_pool.create(cr, uid, line_data, context=context)
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int,long)):
            ids = [ids]
        res = super(delivery_carrier, self).write(cr, uid, ids, vals, context=context)
        self.create_grid_lines(cr, uid, ids, vals, context=context)
        return res

    def create(self, cr, uid, vals, context=None):
        res_id = super(delivery_carrier, self).create(cr, uid, vals, context=context)
        self.create_grid_lines(cr, uid, [res_id], vals, context=context)
        return res_id
