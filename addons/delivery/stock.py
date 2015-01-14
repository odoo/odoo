# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from openerp.osv import fields,osv
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp

# Overloaded stock_picking to manage carriers :
class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _cal_weight(self, cr, uid, ids, name, args, context=None):
        res = {}
        uom_obj = self.pool.get('product.uom')
        for picking in self.browse(cr, uid, ids, context=context):
            total_weight = total_weight_net = 0.00

            for move in picking.move_lines:
                total_weight += move.weight
                total_weight_net += move.weight_net

            res[picking.id] = {
                                'weight': total_weight,
                                'weight_net': total_weight_net,
                              }
        return res


    def _get_picking_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[line.picking_id.id] = True
        return result.keys()

    _columns = {
        'carrier_id':fields.many2one("delivery.carrier","Carrier"),
        'volume': fields.float('Volume'),
        'weight': fields.function(_cal_weight, type='float', string='Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_weight',
                  store={
                 'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                 'stock.move': (_get_picking_line, ['product_id','product_qty','product_uom','product_uos_qty'], 20),
                 }),
        'weight_net': fields.function(_cal_weight, type='float', string='Net Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_weight',
                  store={
                 'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                 'stock.move': (_get_picking_line, ['product_id','product_qty','product_uom','product_uos_qty'], 20),
                 }),
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=32),
        'number_of_packages': fields.integer('Number of Packages'),
        'weight_uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True,readonly="1",help="Unit of measurement for Weight",),
        }

    def _prepare_shipping_invoice_line(self, cr, uid, picking, invoice, context=None):
        """Prepare the invoice line to add to the shipping costs to the shipping's
           invoice.

            :param browse_record picking: the stock picking being invoiced
            :param browse_record invoice: the stock picking's invoice
            :return: dict containing the values to create the invoice line,
                     or None to create nothing
        """
        carrier_obj = self.pool.get('delivery.carrier')
        grid_obj = self.pool.get('delivery.grid')
        if not picking.carrier_id or \
            any(inv_line.product_id.id == picking.carrier_id.product_id.id
                for inv_line in invoice.invoice_line):
            return None
        grid_id = carrier_obj.grid_get(cr, uid, [picking.carrier_id.id],
                picking.partner_id.id, context=context)
        if not grid_id:
            raise osv.except_osv(_('Warning!'),
                    _('The carrier %s (id: %d) has no delivery grid!') \
                            % (picking.carrier_id.name,
                                picking.carrier_id.id))
        price = grid_obj.get_price_from_picking(cr, uid, grid_id,
                invoice.amount_untaxed, picking.weight, picking.volume,
                context=context)
        account_id = picking.carrier_id.product_id.property_account_income.id
        if not account_id:
            account_id = picking.carrier_id.product_id.categ_id\
                    .property_account_income_categ.id

        taxes = picking.carrier_id.product_id.taxes_id
        partner = picking.partner_id or False
        if partner:
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, partner.property_account_position, account_id)
            taxes_ids = self.pool.get('account.fiscal.position').map_tax(cr, uid, partner.property_account_position, taxes)
        else:
            taxes_ids = [x.id for x in taxes]

        return {
            'name': picking.carrier_id.name,
            'invoice_id': invoice.id,
            'uos_id': picking.carrier_id.product_id.uos_id.id,
            'product_id': picking.carrier_id.product_id.id,
            'account_id': account_id,
            'price_unit': price,
            'quantity': 1,
            'invoice_line_tax_id': [(6, 0, taxes_ids)],
        }

    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        picking_obj = self.pool.get('stock.picking')
        invoice_line_obj = self.pool.get('account.invoice.line')
        result = super(stock_picking, self).action_invoice_create(cr, uid,
                ids, journal_id=journal_id, group=group, type=type,
                context=context)
        for picking in picking_obj.browse(cr, uid, result.keys(), context=context):
            invoice = invoice_obj.browse(cr, uid, result[picking.id], context=context)
            invoice_line = self._prepare_shipping_invoice_line(cr, uid, picking, invoice, context=context)
            if invoice_line:
                invoice_line_obj.create(cr, uid, invoice_line)
                invoice_obj.button_compute(cr, uid, [invoice.id], context=context)
        return result
    def _get_default_uom(self,cr,uid,c):
        uom_categ, uom_categ_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'product', 'product_uom_categ_kgm')
        return self.pool.get('product.uom').search(cr, uid, [('category_id', '=', uom_categ_id),('factor','=',1)])[0]
    _defaults = {
        'weight_uom_id': lambda self,cr,uid,c: self._get_default_uom(cr,uid,c)
    }

    def copy(self, cr, uid, id, default=None, context=None):
        default = dict(default or {},
            number_of_packages=0,
            carrier_tracking_ref=False,
            volume=0.0)
        return super(stock_picking, self).copy(cr, uid, id, default=default, context=context)

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        res = super(stock_picking, self).do_partial(cr, uid, ids, partial_datas, context=context)
        for backorder_id, picking_vals in res.iteritems():
            if backorder_id != picking_vals.get('delivered_picking'):
                # delivery info is set on backorder but not on new picking
                backorder = self.browse(cr, uid, backorder_id, context=context)
                self.write(cr, uid, picking_vals['delivered_picking'], {
                    'carrier_tracking_ref': backorder.carrier_tracking_ref,
                    'number_of_packages': backorder.number_of_packages,
                    'volume': backorder.volume,
                }, context=context)
                # delivery info are not relevant to backorder
                self.write(cr, uid, backorder_id, {
                    'carrier_tracking_ref': False,
                    'number_of_packages': 0,
                    'volume': 0,
                }, context=context)

        return res


class stock_move(osv.osv):
    _inherit = 'stock.move'

    def _cal_move_weight(self, cr, uid, ids, name, args, context=None):
        res = {}
        uom_obj = self.pool.get('product.uom')
        for move in self.browse(cr, uid, ids, context=context):
            weight = weight_net = 0.00
            if move.product_id.weight > 0.00:
                converted_qty = move.product_qty

                if move.product_uom.id <> move.product_id.uom_id.id:
                    converted_qty = uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, move.product_id.uom_id.id)

                weight = (converted_qty * move.product_id.weight)

                if move.product_id.weight_net > 0.00:
                    weight_net = (converted_qty * move.product_id.weight_net)

            res[move.id] =  {
                            'weight': weight,
                            'weight_net': weight_net,
                            }
        return res

    def _prepare_chained_picking(self, cr, uid, picking_name, picking, picking_type, moves_todo, context=None):
        values = super(stock_move, self)._prepare_chained_picking(cr, uid, picking_name, picking, picking_type, moves_todo, context=context)
        if picking.carrier_id:
            values['carrier_id'] = picking.carrier_id.id
        values['volume'] = picking.volume
        values['weight'] = picking.weight
        values['weight_net'] = picking.weight_net
        values['carrier_tracking_ref'] = picking.carrier_tracking_ref
        values['number_of_packages'] = picking.number_of_packages
        return values

    _columns = {
        'weight': fields.function(_cal_move_weight, type='float', string='Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_move_weight',
                  store={
                 'stock.move': (lambda self, cr, uid, ids, c=None: ids, ['product_id', 'product_qty', 'product_uom'], 20),
                 }),
        'weight_net': fields.function(_cal_move_weight, type='float', string='Net weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_move_weight',
                  store={
                 'stock.move': (lambda self, cr, uid, ids, c=None: ids, ['product_id', 'product_qty', 'product_uom'], 20),
                 }),
        'weight_uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True,readonly="1",help="Unit of Measure (Unit of Measure) is the unit of measurement for Weight",),
        }
    def _get_default_uom(self,cr,uid,c):
        uom_categ, uom_categ_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'product', 'product_uom_categ_kgm')
        return self.pool.get('product.uom').search(cr, uid, [('category_id', '=', uom_categ_id),('factor','=',1)])[0]
    _defaults = {
        'weight_uom_id': lambda self,cr,uid,c: self._get_default_uom(cr,uid,c)
    }
stock_move()

# Redefinition of the new fields in order to update the model stock.picking.out in the orm
# FIXME: this is a temporary workaround because of a framework bug (ref: lp996816). It should be removed as soon as
#        the bug is fixed

# TODO in trunk: Remove the duplication below using a mixin class!

class stock_picking_out(osv.osv):
    _inherit = 'stock.picking.out'

    def _cal_weight(self, cr, uid, ids, name, args, context=None):
        return self.pool.get('stock.picking')._cal_weight(cr, uid, ids, name, args, context=context)


    def _get_picking_line(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking')._get_picking_line(cr, uid, ids, context=context)

    _columns = {
        'carrier_id':fields.many2one("delivery.carrier","Carrier"),
        'volume': fields.float('Volume'),
        'weight': fields.function(_cal_weight, type='float', string='Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_weight',
                  store={
                 'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                 'stock.move': (_get_picking_line, ['product_id','product_qty','product_uom','product_uos_qty'], 20),
                 }),
        'weight_net': fields.function(_cal_weight, type='float', string='Net Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_weight',
                  store={
                 'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                 'stock.move': (_get_picking_line, ['product_id','product_qty','product_uom','product_uos_qty'], 20),
                 }),
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=32),
        'number_of_packages': fields.integer('Number of Packages'),
        'weight_uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True,readonly="1",help="Unit of measurement for Weight",),
        }
stock_picking_out()

class stock_picking_in(osv.osv):
    _inherit = 'stock.picking.in'

    def _cal_weight(self, cr, uid, ids, name, args, context=None):
        return self.pool.get('stock.picking')._cal_weight(cr, uid, ids, name, args, context=context)

    def _get_picking_line(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking')._get_picking_line(cr, uid, ids, context=context)

    _columns = {
        'carrier_id':fields.many2one("delivery.carrier","Carrier"),
        'volume': fields.float('Volume'),
        'weight': fields.function(_cal_weight, type='float', string='Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_weight',
                store={
                'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                'stock.move': (_get_picking_line, ['product_id','product_qty','product_uom','product_uos_qty'], 20),
                }),
        'weight_net': fields.function(_cal_weight, type='float', string='Net Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_weight',
                store={
                'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                'stock.move': (_get_picking_line, ['product_id','product_qty','product_uom','product_uos_qty'], 20),
                }),
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=32),
        'number_of_packages': fields.integer('Number of Packages'),
        'weight_uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True,readonly="1",help="Unit of measurement for Weight",),
        }
stock_picking_in()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

