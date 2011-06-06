# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
import decimal_precision as dp

class sale_order_line(osv.osv):

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        line_ids = []
        for id in ids:
            res[id] = 0.0
        for line in self.browse(cr, uid, ids, context=context):
            if line.layout_type == 'article':
                line_ids.append(line.id)
        if line_ids:
            res_article = super(sale_order_line, self)._amount_line(cr, uid, line_ids, field_name, arg, context)
            res.update(res_article)
        return res

    def invoice_line_create(self, cr, uid, ids, context=None):
        new_ids = []
        list_seq = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.layout_type == 'article':
                new_ids.append(line.id)
                list_seq.append(line.sequence)
        invoice_line_ids = super(sale_order_line, self).invoice_line_create(cr, uid, new_ids, context)
        pool_inv_line = self.pool.get('account.invoice.line')
        seq = 0
        for obj_inv_line in pool_inv_line.browse(cr, uid, invoice_line_ids, context=context):
            pool_inv_line.write(cr, uid, [obj_inv_line.id], {'sequence': list_seq[seq]}, context=context)
            seq += 1
        return invoice_line_ids

    def onchange_sale_order_line_view(self, cr, uid, id, type, context={}, *args):
        temp = {}
        temp['value'] = {}
        if (not type):
            return {}
        if type != 'article':
            temp = {
                'value': {
                'product_id': False,
                'uos_id': False,
                'account_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'quantity': 0,
                'discount': 0.0,
                'invoice_line_tax_id': False,
                'account_analytic_id': False,
                'product_uom_qty': 0.0,
                },
            }
            if type == 'line':
                temp['value']['name'] = ' '
            if type == 'break':
                temp['value']['name'] = ' '
            if type == 'subtotal':
                temp['value']['name'] = 'Sub Total'
            return temp
        return {}

    def create(self, cr, user, vals, context=None):
        if vals.has_key('layout_type'):
            if vals['layout_type'] == 'line':
                vals['name'] = ' '
            if vals['layout_type'] == 'break':
                vals['name'] = ' '
            if vals['layout_type'] != 'article':
                vals['product_uom_qty']= 0
        return super(sale_order_line, self).create(cr, user, vals, context)

    def write(self, cr, user, ids, vals, context=None):
        if vals.has_key('layout_type'):
            if vals['layout_type'] == 'line':
                vals['name'] = ' '
            if vals['layout_type'] == 'break':
                vals['name'] = ' '
        return super(sale_order_line, self).write(cr, user, ids, vals, context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['layout_type'] = self.browse(cr, uid, id, context=context).layout_type
        return super(sale_order_line, self).copy(cr, uid, id, default, context)

    _order = "order_id, sequence asc"
    _description = "Sales Order line"
    _inherit = "sale.order.line"
    _columns = {
        'layout_type': fields.selection([
                ('article', 'Product'),
                ('title', 'Title'),
                ('text', 'Note'),
                ('subtotal', 'Sub Total'),
                ('line', 'Separator Line'),
                ('break', 'Page Break'),]
            ,'Layout Type', select=True, required=True),
        'sequence': fields.integer('Layout Sequence'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Sale Price'), readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom_qty': fields.float('Quantity (UoM)', digits=(16,2)),
        'product_uom': fields.many2one('product.uom', 'Product UoM'),
        # Override the field to call the overridden _amount_line function
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal', digits_compute= dp.get_precision('Sale Price')),
    }

    _defaults = {
        'layout_type': 'article',
    }

sale_order_line()

class one2many_mod2(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if not values:
            values = {}
        res = {}
        for id in ids:
            res[id] = []
        ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id, 'in', ids), ('layout_type', '=', 'article')], limit=self._limit)
        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
            res[r[self._fields_id]].append( r['id'] )
        return res


class sale_order(osv.osv):

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['order_line'] = False
        return super(sale_order, self).copy(cr, uid, id, default, context)

    _inherit = "sale.order"
    _columns = {
        'abstract_line_ids': fields.one2many('sale.order.line', 'order_id', 'Order Lines', readonly=True, states={'draft': [('readonly', False)]}),
        'order_line': one2many_mod2('sale.order.line', 'order_id', 'Order Lines', readonly=True, states={'draft': [('readonly', False)]}),
    }

sale_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
