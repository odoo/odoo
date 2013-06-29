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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class sale_order(osv.osv):
    
    _inherit = "sale.order"
    
    
    
    
    
    def action_ship_create(self, cr, uid, ids, context=None):
        print "acitonshipcreate"
        for order in self.browse(cr, uid, ids, context=context):
            self._create_pickings_and_procurements(cr, uid, order, order.order_line, None, context=context)
        return True
    
    
    def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Create the required procurements to supply sales order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sales order's requested location.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise
        a standard outgoing picking will be created to wrap the stock moves, as returned
        by :meth:`~._prepare_order_picking`.

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: sales order to which the order lines belong
        :param list(browse_record) order_lines: sales order line records to procure
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if omitted.
        :return: True
        """
        print "Create pickings and procurements!"
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')
        proc_ids = []

        #Create group
        group_id = self.pool.get("procurement.group").create(cr, uid, {'name': order.name}, context=context)

        for line in order_lines:
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)

#             if line.product_id:
#                 if line.product_id.type in ('product', 'consu'):
#                     if not picking_id:
#                         picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
#                     #move_id = move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, group_id=group_id, context=context))
#                 else:
#                     # a service has no stock move
#                     move_id = False

            #TODO Need to do something instead of warehouse
            if line.product_id:
                proc_id = procurement_obj.create(cr, uid, self._prepare_order_line_procurement(cr, uid, order, line, [], date_planned, group_id = group_id, context=context))
                proc_ids.append(proc_id)
                line.write({'procurement_id': proc_id})
                #self.ship_recreate(cr, uid, order, line, move_id, proc_id)

#         if picking_id:
#             picking_obj.signal_button_confirm(cr, uid, [picking_id])
        procurement_obj.signal_button_confirm(cr, uid, proc_ids)

        val = {}
        if order.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

            if (order.order_policy == 'manual'):
                for line in order.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
        order.write(val)
        return True



    def _prepare_order_line_procurement(self, cr, uid, order, line, move_id, date_planned, group_id = False, context=None):
        mod_obj = self.pool.get('ir.model.data')
        location_model, location_id = mod_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')
        output_id = order.warehouse_id.lot_output_id.id
        return {
            'name': line.name,
            'origin': order.name,
            'date_planned': date_planned,
            'product_id': line.product_id.id,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty)\
                    or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'location_id': location_id, 
            'procure_method': line.type,
            'move_id': move_id,
            'company_id': order.company_id.id,
            'note': line.name,
            'group_id': group_id,
            'state': 'draft',  
        }
