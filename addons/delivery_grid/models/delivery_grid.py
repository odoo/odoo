# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields, osv
from openerp.exceptions import UserError
from openerp.tools.translate import _


class delivery_grid(osv.osv):
    _name = "delivery.grid"
    _description = "Delivery Grid"
    _columns = {
        'name': fields.char('Grid Name', required=True),
        'sequence': fields.integer('Sequence', required=True, help="Gives the sequence order when displaying a list of delivery grid."),
        'carrier_id': fields.many2one('delivery.carrier', 'Carrier', required=True, ondelete='cascade'),
        'country_ids': fields.many2many('res.country', 'delivery_grid_country_rel', 'grid_id', 'country_id', 'Countries'),
        'state_ids': fields.many2many('res.country.state', 'delivery_grid_state_rel', 'grid_id', 'state_id', 'States'),
        'zip_from': fields.char('Start Zip', size=12),
        'zip_to': fields.char('To Zip', size=12),
        'line_ids': fields.one2many('delivery.grid.line', 'grid_id', 'Grid Line', copy=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the delivery grid without removing it."),
    }
    _defaults = {
        'active': lambda *a: 1,
        'sequence': lambda *a: 1,
    }
    _order = 'sequence'

    def get_price(self, cr, uid, id, order, dt, context=None):
        total = 0
        weight = 0
        volume = 0
        quantity = 0
        total_delivery = 0.0
        product_uom_obj = self.pool.get('product.uom')
        for line in order.order_line:
            if line.state == 'cancel':
                continue
            if line.is_delivery:
                total_delivery += line.price_subtotal + self.pool['sale.order']._amount_line_tax(cr, uid, line, context=context)
            if not line.product_id or line.is_delivery:
                continue
            q = product_uom_obj._compute_qty(cr, uid, line.product_uom.id, line.product_uom_qty, line.product_id.uom_id.id)
            weight += (line.product_id.weight or 0.0) * q
            volume += (line.product_id.volume or 0.0) * q
            quantity += q
        total = (order.amount_total or 0.0) - total_delivery

        return self.get_price_from_picking(cr, uid, id, total,weight, volume, quantity, context=context)

    def get_price_from_picking(self, cr, uid, id, total, weight, volume, quantity, context=None):
        grid = self.browse(cr, uid, id, context=context)
        price = 0.0
        ok = False
        price_dict = {'price': total, 'volume':volume, 'weight': weight, 'wv':volume*weight, 'quantity': quantity}
        for line in grid.line_ids:
            test = eval(line.type+line.operator+str(line.max_value), price_dict)
            if test:
                if line.price_type=='variable':
                    price = line.list_price * price_dict[line.variable_factor]
                else:
                    price = line.list_price
                ok = True
                break
        if not ok:
            raise UserError(_("Selected product in the delivery method doesn't fulfill any of the delivery grid(s) criteria."))

        return price


class delivery_grid_line(osv.osv):
    _name = "delivery.grid.line"
    _description = "Delivery Grid Line"
    _columns = {
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Sequence', required=True, help="Gives the sequence order when calculating delivery grid."),
        'grid_id': fields.many2one('delivery.grid', 'Grid',required=True, ondelete='cascade'),
        'type': fields.selection([('weight','Weight'),('volume','Volume'),\
                                  ('wv','Weight * Volume'), ('price','Price'), ('quantity','Quantity')],\
                                  'Variable', required=True),
        'operator': fields.selection([('==','='),('<=','<='),('<','<'),('>=','>='),('>','>')], 'Operator', required=True),
        'max_value': fields.float('Maximum Value', required=True),
        'price_type': fields.selection([('fixed','Fixed'),('variable','Variable')], 'Price Type', required=True),
        'variable_factor': fields.selection([('weight','Weight'),('volume','Volume'),('wv','Weight * Volume'), ('price','Price'), ('quantity','Quantity')], 'Variable Factor', required=True),
        'list_price': fields.float('Sale Price', digits_compute= dp.get_precision('Product Price'), required=True),
        'standard_price': fields.float('Cost Price', digits_compute= dp.get_precision('Product Price'), required=True),
    }
    _defaults = {
        'sequence': lambda *args: 10,
        'type': lambda *args: 'weight',
        'operator': lambda *args: '<=',
        'price_type': lambda *args: 'fixed',
        'variable_factor': lambda *args: 'weight',
    }
    _order = 'sequence, list_price'
