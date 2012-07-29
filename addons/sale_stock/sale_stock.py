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
from datetime import datetime, timedelta
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from dateutil.relativedelta import relativedelta
from osv import fields, osv
import netsvc
from tools.translate import _

class sale_shop(osv.osv):
    _inherit = "sale.shop"
    _columns = {
            'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
    }

class sale_order(osv.osv):
    _inherit = "sale.order"
    
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'shipped': False,
            'picking_ids': [],
        })
        return super(sale_order, self).copy(cr, uid, id, default, context=context)
    
    def shipping_policy_change(self, cr, uid, ids, policy, context=None):
        if not policy:
            return {}
        inv_qty = 'order'
        if policy == 'prepaid':
            inv_qty = 'order'
        elif policy == 'picking':
            inv_qty = 'procurement'
        return {'value': {'invoice_quantity': inv_qty}}

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('order_policy', False):
            if vals['order_policy'] == 'prepaid':
                vals.update({'invoice_quantity': 'order'})
            elif vals['order_policy'] == 'picking':
                vals.update({'invoice_quantity': 'procurement'})
        return super(sale_order, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        if vals.get('order_policy', False):
            if vals['order_policy'] == 'prepaid':
                vals.update({'invoice_quantity': 'order'})
            if vals['order_policy'] == 'picking':
                vals.update({'invoice_quantity': 'procurement'})
        order =  super(sale_order, self).create(cr, uid, vals, context=context)
        return order

    # This is False
    def _picked_rate(self, cr, uid, ids, name, arg, context=None):
        if not ids:
            return {}
        res = {}
        tmp = {}
        for id in ids:
            tmp[id] = {'picked': 0.0, 'total': 0.0}
        cr.execute('''SELECT
                p.sale_id as sale_order_id, sum(m.product_qty) as nbr, mp.state as procurement_state, m.state as move_state, p.type as picking_type
            FROM
                stock_move m
            LEFT JOIN
                stock_picking p on (p.id=m.picking_id)
            LEFT JOIN
                procurement_order mp on (mp.move_id=m.id)
            WHERE
                p.sale_id IN %s GROUP BY m.state, mp.state, p.sale_id, p.type''', (tuple(ids),))

        for item in cr.dictfetchall():
            if item['move_state'] == 'cancel':
                continue

            if item['picking_type'] == 'in':#this is a returned picking
                tmp[item['sale_order_id']]['total'] -= item['nbr'] or 0.0 # Deducting the return picking qty
                if item['procurement_state'] == 'done' or item['move_state'] == 'done':
                    tmp[item['sale_order_id']]['picked'] -= item['nbr'] or 0.0
            else:
                tmp[item['sale_order_id']]['total'] += item['nbr'] or 0.0
                if item['procurement_state'] == 'done' or item['move_state'] == 'done':
                    tmp[item['sale_order_id']]['picked'] += item['nbr'] or 0.0

        for order in self.browse(cr, uid, ids, context=context):
            if order.shipped:
                res[order.id] = 100.0
            else:
                res[order.id] = tmp[order.id]['total'] and (100.0 * tmp[order.id]['picked'] / tmp[order.id]['total']) or 0.0
        return res
    
    _columns = {
        'state': fields.selection([
            ('draft', 'Draft Quotation'),
            ('sent', 'Quotation Sent'),
            ('cancel', 'Cancelled'),
            ('waiting_date', 'Waiting Schedule'),
            ('progress', 'Sale Order'),
            ('manual', 'Sale to Invoice'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ], 'Status', readonly=True,help="Gives the state of the quotation or sales order.\
              \nThe exception state is automatically set when a cancel operation occurs \
              in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' state is set when the invoice is confirmed\
               but waiting for the scheduler to run on the order date.", select=True),
        'incoterm': fields.many2one('stock.incoterms', 'Incoterm', help="Incoterm which stands for 'International Commercial terms' implies its a series of sales terms which are used in the commercial transaction."),
        'picking_policy': fields.selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')],
            'Shipping Policy', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""If you don't have enough stock available to deliver all at once, do you accept partial shipments or not?"""),
        'order_policy': fields.selection([
                ('manual', 'On Demand'),
                ('picking', 'On Delivery Order'),
                ('prepaid', 'Before Delivery'),
            ], 'Create Invoice', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""This field controls how invoice and delivery operations are synchronized.
                  - With 'On Demand', the invoice is created manually when needed.
                  - With 'On Delivery Order', a draft invoice is generated after all pickings have been processed.
                  - With 'Before Delivery', a draft invoice is created, and it must be paid before delivery."""),
        'picking_ids': fields.one2many('stock.picking.out', 'sale_id', 'Related Picking', readonly=True, help="This is a list of delivery orders that has been generated for this sales order."),
        'shipped': fields.boolean('Delivered', readonly=True, help="It indicates that the sales order has been delivered. This field is updated only after the scheduler(s) have been launched."),
        'picked_rate': fields.function(_picked_rate, string='Picked', type='float'),
        'invoice_quantity': fields.selection([('order', 'Ordered Quantities'), ('procurement', 'Shipped Quantities')], 'Invoice on', 
                                             help="The sale order will automatically create the invoice proposition (draft invoice).\
                                              You have to choose  if you want your invoice based on ordered ", required=True, readonly=True, states={'draft': [('readonly', False)]}),                  
    }
    _defaults = {
             'picking_policy': 'direct',
             'order_policy': 'manual',
             'invoice_quantity': 'order',
         }

    # Form filling
    def unlink(self, cr, uid, ids, context=None):
        sale_orders = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in sale_orders:
            if s['state'] in ['draft', 'cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('In order to delete a confirmed sale order, you must cancel it before ! To cancel a sale order, you must first cancel related picking or delivery orders.'))

        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)    
    
    
    
    def action_view_delivery(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing delivery orders of given sale order ids. It can either be a in a list or in a form view, if there is only one delivery order to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        result = {
            'name': _('Delivery Order'),
            'view_type': 'form',
            'res_model': 'stock.picking',
            'context': "{'type':'out'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }
        #compute the number of delivery orders to display
        pick_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in so.picking_ids]
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_out_tree')
            result.update({
                'view_mode': 'tree,form',
                'res_id': pick_ids or False
            })
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_out_form')
            result.update({
                'view_mode': 'form',
                'res_id': pick_ids and pick_ids[0] or False,
            })
        result.update(view_id = res and res[1] or False)
        return result
    
    def action_wait(self, cr, uid, ids, context=None):
        for o in self.browse(cr, uid, ids):
            if not o.order_line:
                raise osv.except_osv(_('Error !'),_('You cannot confirm a sale order which has no line.'))
            if (o.order_policy == 'manual'):
                self.write(cr, uid, [o.id], {'state': 'manual', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            else:
               self.write(cr, uid, [o.id], {'state': 'progress', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            self.pool.get('sale.order.line').button_confirm(cr, uid, [x.id for x in o.order_line])
            self.confirm_send_note(cr, uid, ids, context)
        return True
    
    def manual_invoice(self, cr, uid, ids, context=None):
        """ create invoices for the given sale orders (ids), and open the form
            view of one of the newly created invoices
        """
        mod_obj = self.pool.get('ir.model.data')
        wf_service = netsvc.LocalService("workflow")

        # create invoices through the sale orders' workflow
        inv_ids0 = set(inv.id for sale in self.browse(cr, uid, ids, context) for inv in sale.invoice_ids)
        for id in ids:
            wf_service.trg_validate(uid, 'sale.order', id, 'manual_invoice', cr)
        inv_ids1 = set(inv.id for sale in self.browse(cr, uid, ids, context) for inv in sale.invoice_ids)
        # determine newly created invoices
        new_inv_ids = list(inv_ids1 - inv_ids0)

        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False,

        return {
            'name': _('Customer Invoices'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': new_inv_ids and new_inv_ids[0] or False,
        }
    
        
    
    def action_invoice_create(self, cr, uid, ids, grouped=False, states=['confirmed', 'done', 'exception'], date_inv = False, context=None):
        res = super(sale_order,self).action_invoice_create( cr, uid, ids, grouped=grouped, states=states, date_inv = date_inv, context=context)
        picking_obj = self.pool.get('stock.picking')
        if context is None:
            context = {}
        # If date was specified, use it as date invoiced, usefull when invoices are generated this month and put the
        # last day of the last month as invoice date
        for order in self.browse(cr, uid, ids, context=context):
            if order.order_policy == 'picking':
                picking_obj.write(cr, uid, map(lambda x: x.id, order.picking_ids), {'invoice_state': 'invoiced'})
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}
        sale_order_line_obj = self.pool.get('sale.order.line')
        proc_obj = self.pool.get('procurement.order')
        for sale in self.browse(cr, uid, ids, context=context):
            for pick in sale.picking_ids:
                if pick.state not in ('draft', 'cancel'):
                    raise osv.except_osv(
                        _('Could not cancel sales order !'),
                       _('You must first cancel all picking attached to this sales order.'))
                if pick.state == 'cancel':
                    for mov in pick.move_lines:
                        proc_ids = proc_obj.search(cr, uid, [('move_id', '=', mov.id)])
                        if proc_ids:
                            for proc in proc_ids:
                                wf_service.trg_validate(uid, 'procurement.order', proc, 'button_check', cr)
            for r in self.read(cr, uid, ids, ['picking_ids']):
               for pick in r['picking_ids']:
                    wf_service.trg_validate(uid, 'stock.picking', pick, 'button_cancel', cr)
        return super(sale_order, self).action_cancel(cr, uid, ids, context=context)

    def procurement_lines_get(self, cr, uid, ids, *args):
        res = []
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.order_line:
                if line.procurement_id:
                    res.append(line.procurement_id.id)
        return res

    # if mode == 'finished':
    #   returns True if all lines are done, False otherwise
    # if mode == 'canceled':
    #   returns True if there is at least one canceled line, False otherwise
    def test_state(self, cr, uid, ids, mode, *args):
        assert mode in ('finished', 'canceled'), _("invalid mode for test_state")
        finished = True
        canceled = False
        notcanceled = False
        write_done_ids = []
        write_cancel_ids = []
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.order_line:
                if (not line.procurement_id) or (line.procurement_id.state=='done'):
                    if line.state != 'done':
                        write_done_ids.append(line.id)
                else:
                    finished = False
                if line.procurement_id:
                    if (line.procurement_id.state == 'cancel'):
                        canceled = True
                        if line.state != 'exception':
                            write_cancel_ids.append(line.id)
                    else:
                        notcanceled = True
        if write_done_ids:
            self.pool.get('sale.order.line').write(cr, uid, write_done_ids, {'state': 'done'})
        if write_cancel_ids:
            self.pool.get('sale.order.line').write(cr, uid, write_cancel_ids, {'state': 'exception'})

        if mode == 'finished':
            return finished
        elif mode == 'canceled':
            return canceled
            if notcanceled:
                return False
            return canceled

    def _prepare_order_line_procurement(self, cr, uid, order, line, move_id, date_planned, context=None):
        return {
            'name': line.name.split('\n')[0],
            'origin': order.name,
            'date_planned': date_planned,
            'product_id': line.product_id.id,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty)\
                    or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
            'procure_method': line.type,
            'move_id': move_id,
            'company_id': order.company_id.id,
            'note': '\n'.join(line.name.split('\n')[1:]),
            'property_ids': [(6, 0, [x.id for x in line.property_ids])]
        }

    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        location_id = order.shop_id.warehouse_id.lot_stock_id.id
        output_id = order.shop_id.warehouse_id.lot_output_id.id
        return {
            'name': line.name.split('\n')[0][:250],
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'product_packaging': line.product_packaging.id,
            'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
            'location_id': location_id,
            'location_dest_id': output_id,
            'sale_line_id': line.id,
            'tracking_id': False,
            'state': 'draft',
            #'state': 'waiting',
            'note': '\n'.join(line.name.split('\n')[1:]),
            'company_id': order.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0
        }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        return {
            'name': pick_name,
            'origin': order.name,
            'date': order.date_order,
            'type': 'out',
            'state': 'auto',
            'move_type': order.picking_policy,
            'sale_id': order.id,
            'partner_id': order.partner_shipping_id.id,
            'note': order.note,
            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
            'company_id': order.company_id.id,
        }

    def ship_recreate(self, cr, uid, order, line, move_id, proc_id):
        # FIXME: deals with potentially cancelled shipments, seems broken (specially if shipment has production lot)
        """
        Define ship_recreate for process after shipping exception
        param order: sale order to which the order lines belong
        param line: sale order line records to procure
        param move_id: the ID of stock move
        param proc_id: the ID of procurement
        """
        move_obj = self.pool.get('stock.move')
        if order.state == 'shipping_except':
            for pick in order.picking_ids:
                for move in pick.move_lines:
                    if move.state == 'cancel':
                        mov_ids = move_obj.search(cr, uid, [('state', '=', 'cancel'),('sale_line_id', '=', line.id),('picking_id', '=', pick.id)])
                        if mov_ids:
                            for mov in move_obj.browse(cr, uid, mov_ids):
                                # FIXME: the following seems broken: what if move_id doesn't exist? What if there are several mov_ids? Shouldn't that be a sum?
                                move_obj.write(cr, uid, [move_id], {'product_qty': mov.product_qty, 'product_uos_qty': mov.product_uos_qty})
                                self.pool.get('procurement.order').write(cr, uid, [proc_id], {'product_qty': mov.product_qty, 'product_uos_qty': mov.product_uos_qty})
        return True

    def _get_date_planned(self, cr, uid, order, line, start_date, context=None):
        date_planned = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=line.delay or 0.0)
        date_planned = (date_planned - timedelta(days=order.company_id.security_lead)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return date_planned

    def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Create the required procurements to supply sale order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sale order's requested location.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise
        a standard outgoing picking will be created to wrap the stock moves, as returned
        by :meth:`~._prepare_order_picking`.

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: sale order to which the order lines belong
        :param list(browse_record) order_lines: sale order line records to procure
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if ommitted.
        :return: True
        """
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')
        proc_ids = []

        for line in order_lines:
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)

            if line.product_id:
                if line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    if not picking_id:
                        picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
                    move_id = move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context))
                else:
                    # a service has no stock move
                    move_id = False

                proc_id = procurement_obj.create(cr, uid, self._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context))
                proc_ids.append(proc_id)
                line.write({'procurement_id': proc_id})
                self.ship_recreate(cr, uid, order, line, move_id, proc_id)

        wf_service = netsvc.LocalService("workflow")
        if picking_id:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            self.delivery_send_note(cr, uid, [order.id], picking_id, context)


        for proc_id in proc_ids:
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

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

    def action_ship_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            self._create_pickings_and_procurements(cr, uid, order, order.order_line, None, context=context)
        return True

    def action_ship_end(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            val = {'shipped': True}
            if order.state == 'shipping_except':
                val['state'] = 'progress'
                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
            for line in order.order_line:
                towrite = []
                if line.state == 'exception':
                    towrite.append(line.id)
                if towrite:
                    self.pool.get('sale.order.line').write(cr, uid, towrite, {'state': 'done'}, context=context)
            res = self.write(cr, uid, [order.id], val)
            if res:
                self.delivery_end_send_note(cr, uid, [order.id], context=context)
        return True

    def has_stockable_products(self, cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.product_id and order_line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    return True
        return False
    # ------------------------------------------------
    # OpenChatter methods and notifications
    # ------------------------------------------------
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        result = super(sale_order, self).get_needaction_user_ids(cr, uid, ids, context=context)
        for obj in self.browse(cr, uid, ids, context=context):
            if (obj.state == 'manual' or obj.state == 'progress'):
                result[obj.id].append(obj.user_id.id)
        return result

    def delivery_send_note(self, cr, uid, ids, picking_id, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            for picking in (pck for pck in order.picking_ids if pck.id == picking_id):
                # convert datetime field to a datetime, using server format, then
                # convert it to the user TZ and re-render it with %Z to add the timezone
                picking_datetime = fields.DT.datetime.strptime(picking.min_date, DEFAULT_SERVER_DATETIME_FORMAT)
                picking_date_str = fields.datetime.context_timestamp(cr, uid, picking_datetime, context=context).strftime(DATETIME_FORMATS_MAP['%+'] + " (%Z)")
                self.message_append_note(cr, uid, [order.id], body=_("Delivery Order <em>%s</em> <b>scheduled</b> for %s.") % (picking.name, picking_date_str), context=context)
    
    def delivery_end_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Order <b>delivered</b>."), context=context)
    
    
class sale_order_line(osv.osv):
    
    def _number_packages(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            try:
                res[line.id] = int((line.product_uom_qty+line.product_packaging.qty-0.0001) / line.product_packaging.qty)
            except:
                res[line.id] = 1
        return res
    
    _inherit = 'sale.order.line'
    _columns = { 
         'delay': fields.float('Delivery Lead Time', required=True, help="Number of days between the order confirmation the shipping of the products to the customer", readonly=True, states={'draft': [('readonly', False)]}),
         'procurement_id': fields.many2one('procurement.order', 'Procurement'),
         'type': fields.selection([('make_to_stock', 'from stock'), ('make_to_order', 'on order')], 'Procurement Method', required=True, readonly=True, states={'draft': [('readonly', False)]},
            help="If 'on order', it triggers a procurement when the sale order is confirmed to create a task, purchase order or manufacturing order linked to this sale order line."),
         'property_ids': fields.many2many('mrp.property', 'sale_order_line_property_rel', 'order_id', 'property_id', 'Properties', readonly=True, states={'draft': [('readonly', False)]}),
        'product_packaging': fields.many2one('product.packaging', 'Packaging'),
        'move_ids': fields.one2many('stock.move', 'sale_line_id', 'Inventory Moves', readonly=True),
        'number_packages': fields.function(_number_packages, type='integer', string='Number Packages'),
                     
    }
    _defaults = {
             'delay': 0.0,
             'type': 'make_to_stock',
             'product_packaging': False,
         }
    
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
        
        def _get_line_qty(line):
            if not (line.order_id.invoice_quantity=='order') or line.procurement_id:
                return self.pool.get('procurement.order').quantity_get(cr, uid,
                        line.procurement_id.id, context=context)
       
        def _get_line_uom(line):
            if not (line.order_id.invoice_quantity=='order') or line.procurement_id:
                return self.pool.get('procurement.order').uom_get(cr, uid,
                        line.procurement_id.id, context=context)
        uosqty = _get_line_qty(line)
        uos_id = _get_line_uom(line)
        if uosqty:
                pu = round(line.price_unit * line.product_uom_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Sale Price'))
        res.update({'price_unit': pu, 'quantity': uosqty,'uos_id': uos_id})
        return res
    
    def product_packaging_change(self, cr, uid, ids, pricelist, product, qty=0, uom=False,
                                   partner_id=False, packaging=False, flag=False, context=None):
        if not product:
            return {'value': {'product_packaging': False}}
        product_obj = self.pool.get('product.product')
        product_uom_obj = self.pool.get('product.uom')
        pack_obj = self.pool.get('product.packaging')
        warning = {}
        result = {}
        warning_msgs = ''
        if flag:
            res = self.product_id_change(cr, uid, ids, pricelist=pricelist,
                    product=product, qty=qty, uom=uom, partner_id=partner_id,
                    packaging=packaging, flag=False, context=context)
            warning_msgs = res.get('warning') and res['warning']['message']

        products = product_obj.browse(cr, uid, product, context=context)
        if not products.packaging:
            packaging = result['product_packaging'] = False
        elif not packaging and products.packaging and not flag:
            packaging = products.packaging[0].id
            result['product_packaging'] = packaging

        if packaging:
            default_uom = products.uom_id and products.uom_id.id
            pack = pack_obj.browse(cr, uid, packaging, context=context)
            q = product_uom_obj._compute_qty(cr, uid, uom, pack.qty, default_uom)
#            qty = qty - qty % q + q
            if qty and (q and not (qty % q) == 0):
                ean = pack.ean or _('(n/a)')
                qty_pack = pack.qty
                type_ul = pack.ul
                if not warning_msgs:
                    warn_msg = _("You selected a quantity of %d Units.\n"
                                "But it's not compatible with the selected packaging.\n"
                                "Here is a proposition of quantities according to the packaging:\n"
                                "EAN: %s Quantity: %s Type of ul: %s") % \
                                    (qty, ean, qty_pack, type_ul.name)
                    warning_msgs += _("Picking Information ! : ") + warn_msg + "\n\n"
                warning = {
                       'title': _('Configuration Error !'),
                       'message': warning_msgs
                }
            result['product_uom_qty'] = qty

        return {'value': result, 'warning': warning}
                              