# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP SA (<http://openerp.com>).
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

import time
from lxml import etree
from openerp.osv import fields, osv
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.float_utils import float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class stock_partial_picking_line(osv.TransientModel):

    def _tracking(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for tracklot in self.browse(cursor, user, ids, context=context):
            tracking = False
            if (tracklot.move_id.picking_id.type == 'in' and tracklot.product_id.track_incoming == True) or \
                (tracklot.move_id.picking_id.type == 'out' and tracklot.product_id.track_outgoing == True):
                tracking = True
            res[tracklot.id] = tracking
        return res

    _name = "stock.partial.picking.line"
    _rec_name = 'product_id'
    _columns = {
        'product_id' : fields.many2one('product.product', string="Product", required=True, ondelete='CASCADE'),
        'quantity' : fields.float("Quantity", digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True, ondelete='CASCADE'),
        'prodlot_id' : fields.many2one('stock.production.lot', 'Serial Number', ondelete='CASCADE'),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete='CASCADE', domain = [('usage','<>','view')]),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True, ondelete='CASCADE',domain = [('usage','<>','view')]),
        'move_id' : fields.many2one('stock.move', "Move", ondelete='CASCADE'),
        'wizard_id' : fields.many2one('stock.partial.picking', string="Wizard", ondelete='CASCADE'),
        'update_cost': fields.boolean('Need cost update'),
        'cost' : fields.float("Cost", help="Unit Cost for this product line", digits_compute=dp.get_precision('Product Price')),
        'currency' : fields.many2one('res.currency', string="Currency", help="Currency in which Unit cost is expressed", ondelete='CASCADE'),
        'tracking': fields.function(_tracking, string='Tracking', type='boolean'),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        uom_id = False
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            uom_id = product.uom_id.id
        return {'value': {'product_uom': uom_id}}


class stock_partial_picking(osv.osv_memory):
    _name = "stock.partial.picking"
    _rec_name = 'picking_id'
    _description = "Partial Picking Processing Wizard"

    def _hide_tracking(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for wizard in self.browse(cursor, user, ids, context=context):
            res[wizard.id] = any([not(x.tracking) for x in wizard.move_ids])
        return res

    _columns = {
        'date': fields.datetime('Date', required=True),
        'move_ids' : fields.one2many('stock.partial.picking.line', 'wizard_id', 'Product Moves'),
        'picking_id': fields.many2one('stock.picking', 'Picking', required=True, ondelete='CASCADE'),
        'hide_tracking': fields.function(_hide_tracking, string='Tracking', type='boolean', help='This field is for internal purpose. It is used to decide if the column production lot has to be shown on the moves or not.'),
     }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        #override of fields_view_get in order to change the label of the process button and the separator accordingly to the shipping type
        if context is None:
            context={}
        res = super(stock_partial_picking, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        type = context.get('default_type', False)
        if type:
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//button[@name='do_partial']"):
                if type == 'in':
                    node.set('string', _('_Receive'))
                elif type == 'out':
                    node.set('string', _('_Deliver'))
            for node in doc.xpath("//separator[@name='product_separator']"):
                if type == 'in':
                    node.set('string', _('Receive Products'))
                elif type == 'out':
                    node.set('string', _('Deliver Products'))
            res['arch'] = etree.tostring(doc)
        return res

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking', 'stock.picking.in', 'stock.picking.out'), 'Bad context propagation'
        picking_id, = picking_ids
        if 'picking_id' in fields:
            res.update(picking_id=picking_id)
        if 'move_ids' in fields:
            picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
            moves = [self._partial_move_for(cr, uid, m) for m in picking.move_lines if m.state not in ('done','cancel')]
            res.update(move_ids=moves)
        if 'date' in fields:
            res.update(date=time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        return res

    def _product_cost_for_average_update(self, cr, uid, move):
        """Returns product cost and currency ID for the given move, suited for re-computing
           the average product cost.

           :return: map of the form::

                {'cost': 123.34,
                 'currency': 42}
        """
        # Currently, the cost on the product form is supposed to be expressed in the currency
        # of the company owning the product. If not set, we fall back to the picking's company,
        # which should work in simple cases.
        product_currency_id = move.product_id.company_id.currency_id and move.product_id.company_id.currency_id.id
        picking_currency_id = move.picking_id.company_id.currency_id and move.picking_id.company_id.currency_id.id
        return {'cost': move.product_id.standard_price,
                'currency': product_currency_id or picking_currency_id or False}

    def _partial_move_for(self, cr, uid, move):
        partial_move = {
            'product_id' : move.product_id.id,
            'quantity' : move.product_qty if move.state == 'assigned' or move.picking_id.type == 'in' else 0,
            'product_uom' : move.product_uom.id,
            'prodlot_id' : move.prodlot_id.id,
            'move_id' : move.id,
            'location_id' : move.location_id.id,
            'location_dest_id' : move.location_dest_id.id,
        }
        if move.picking_id.type == 'in' and move.product_id.cost_method == 'average':
            partial_move.update(update_cost=True, **self._product_cost_for_average_update(cr, uid, move))
        return partial_move

    def do_partial(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        assert len(ids) == 1, 'Partial picking processing may only be done one at a time.'
        stock_picking = self.pool.get('stock.picking')
        stock_move = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date' : partial.date
        }
        picking_type = partial.picking_id.type
        for wizard_line in partial.move_ids:
            line_uom = wizard_line.product_uom
            move_id = wizard_line.move_id.id

            #Quantiny must be Positive
            if wizard_line.quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Please provide proper Quantity.'))

            #Compute the quantity for respective wizard_line in the line uom (this jsut do the rounding if necessary)
            qty_in_line_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, line_uom.id)

            if line_uom.factor and line_uom.factor <> 0:
                if float_compare(qty_in_line_uom, wizard_line.quantity, precision_rounding=line_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _('The unit of measure rounding does not allow you to ship "%s %s", only rounding of "%s %s" is accepted by the Unit of Measure.') % (wizard_line.quantity, line_uom.name, line_uom.rounding, line_uom.name))
            if move_id:
                #Check rounding Quantity.ex.
                #picking: 1kg, uom kg rounding = 0.01 (rounding to 10g),
                #partial delivery: 253g
                #=> result= refused, as the qty left on picking would be 0.747kg and only 0.75 is accepted by the uom.
                initial_uom = wizard_line.move_id.product_uom
                #Compute the quantity for respective wizard_line in the initial uom
                qty_in_initial_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, initial_uom.id)
                without_rounding_qty = (wizard_line.quantity / line_uom.factor) * initial_uom.factor
                if float_compare(qty_in_initial_uom, without_rounding_qty, precision_rounding=initial_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _('The rounding of the initial uom does not allow you to ship "%s %s", as it would let a quantity of "%s %s" to ship and only rounding of "%s %s" is accepted by the uom.') % (wizard_line.quantity, line_uom.name, wizard_line.move_id.product_qty - without_rounding_qty, initial_uom.name, initial_uom.rounding, initial_uom.name))
            else:
                seq_obj_name =  'stock.picking.' + picking_type
                move_id = stock_move.create(cr,uid,{'name' : self.pool.get('ir.sequence').get(cr, uid, seq_obj_name),
                                                    'product_id': wizard_line.product_id.id,
                                                    'product_qty': wizard_line.quantity,
                                                    'product_uom': wizard_line.product_uom.id,
                                                    'prodlot_id': wizard_line.prodlot_id.id,
                                                    'location_id' : wizard_line.location_id.id,
                                                    'location_dest_id' : wizard_line.location_dest_id.id,
                                                    'picking_id': partial.picking_id.id
                                                    },context=context)
                stock_move.action_confirm(cr, uid, [move_id], context)
            partial_data['move%s' % (move_id)] = {
                'product_id': wizard_line.product_id.id,
                'product_qty': wizard_line.quantity,
                'product_uom': wizard_line.product_uom.id,
                'prodlot_id': wizard_line.prodlot_id.id,
            }
            if (picking_type == 'in') and (wizard_line.product_id.cost_method == 'average'):
                partial_data['move%s' % (wizard_line.move_id.id)].update(product_price=wizard_line.cost,
                                                                  product_currency=wizard_line.currency.id)
        
        # Do the partial delivery and open the picking that was delivered
        # We don't need to find which view is required, stock.picking does it.
        done = stock_picking.do_partial(
            cr, uid, [partial.picking_id.id], partial_data, context=context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': context.get('active_model', 'stock.picking'),
            'name': _('Partial Delivery'),
            'res_id': done[partial.picking_id.id]['delivered_picking'],
            'view_type': 'form',
            'view_mode': 'form,tree,calendar',
            'context': context,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
