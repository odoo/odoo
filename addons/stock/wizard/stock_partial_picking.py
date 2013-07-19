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
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class stock_partial_picking_line(osv.TransientModel):

    def _tracking(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for tracklot in self.browse(cursor, user, ids, context=context):
            if not tracklot.move_id:
                continue
            tracking = False
            if (tracklot.move_id.picking_id.type == 'in' and tracklot.product_id.track_incoming) or \
               (tracklot.move_id.picking_id.type == 'out' and tracklot.product_id.track_outgoing):
                tracking = True
            res[tracklot.id] = tracking
        return res

    _name = "stock.partial.picking.line"
    _rec_name = 'product_id'
    _columns = {
        'product_id': fields.many2one('product.product', string="Product", required=True, ondelete='CASCADE'),
        'quantity': fields.float("Quantity", digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True, ondelete='CASCADE'),
        'lot_id': fields.many2one('stock.production.lot', 'Serial Number', ondelete='CASCADE'),
        'move_id': fields.many2one('stock.move', "Move", ondelete='CASCADE'),
        'wizard_id': fields.many2one('stock.partial.picking', string="Wizard", ondelete='CASCADE'),
        'update_cost': fields.boolean('Need cost update'),
        'cost': fields.float("Cost", help="Unit Cost for this product line"),
        'currency': fields.many2one('res.currency', string="Currency", help="Currency in which Unit cost is expressed", ondelete='CASCADE'),
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
        'move_ids': fields.one2many('stock.partial.picking.line', 'wizard_id', 'Product Moves'),
        'picking_id': fields.many2one('stock.picking', 'Picking', required=True, ondelete='CASCADE'),
        'hide_tracking': fields.function(_hide_tracking, string='Tracking', type='boolean', help='This field is for internal purpose. It is used to decide if the column production lot has to be shown on the moves or not.'),
        'only_split_lines': fields.boolean('Only Split', help="Check this field if you just want to split the picking and don't want to marke as done the lines in the backorder"),
     }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        #override of fields_view_get in order to change the label of the process button and the separator accordingly to the shipping type
        if context is None:
            context = {}
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
        if context is None:
            context = {}
        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking', 'stock.picking.in', 'stock.picking.out'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        if 'picking_id' in fields:
            res.update(picking_id=picking_id)
        if 'move_ids' in fields:
            moves = [self._partial_move_for(cr, uid, m) for m in picking.move_lines if m.state not in ('done', 'cancel')]
            res.update(move_ids=moves)
        if 'date' in fields:
            res.update(date=time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        return res

    def _partial_move_for(self, cr, uid, move):
        partial_move = {
            'product_id': move.product_id.id,
            'quantity': move.product_uom_qty,
            'product_uom': move.product_uom.id,
            'move_id': move.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'cost': move.product_id.standard_price,
        }
        return partial_move

    def do_partial(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'Partial picking processing may only be done one at a time.'
        if context is None:
            context = {}
        stock_move_obj = self.pool.get('stock.move')
        partial_wizard = self.browse(cr, uid, ids[0], context=context)
        picking_id = partial_wizard.picking_id.id
        assert picking_id, 'Picking not defined'
        picking_type = partial_wizard.picking_id.type

        partial_data = {
            'delivery_date': partial_wizard.date
        }

        partial_datas = []
        for wizard_line in partial_wizard.move_ids:
            move_id = wizard_line.move_id.id
            if not move_id:
                seq_obj_name = 'stock.picking.' + picking_type
                move_id = stock_move_obj.create(cr, uid, {'name': self.pool.get('ir.sequence').get(cr, uid, seq_obj_name),
                                                    'product_id': wizard_line.product_id.id,
                                                    'product_uom_qty': wizard_line.quantity,
                                                    'product_uom': wizard_line.product_uom.id,
                                                    'lot_id': wizard_line.lot_id.id,
                                                    'location_id': partial_wizard.picking_id.location_id.id,
                                                    'location_dest_id': partial_wizard.picking_id.location_dest_id.id,
                                                    'picking_id': False,
                                                    'price_unit': wizard_line.cost}, context=context)
            partial_data.update({
                'product_id': wizard_line.product_id.id,
                'product_uom_qty': wizard_line.quantity,
                'product_uom': wizard_line.product_uom.id,
                'lot_id': wizard_line.lot_id.id,
                'price_unit': wizard_line.cost,
                'move_id': move_id,
            })
            tmp = partial_data.copy()
            partial_datas += [tmp]
        self.pool.get('stock.picking').do_partial(cr, uid, picking_id, partial_datas, partial_wizard.only_split_lines, context=context)
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
