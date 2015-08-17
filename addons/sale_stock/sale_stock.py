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
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp.osv import fields, osv
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
import pytz
from openerp import SUPERUSER_ID

class sale_order(osv.osv):
    _inherit = "sale.order"

    def _get_default_warehouse(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [('company_id', '=', company_id)], context=context)
        if not warehouse_ids:
            return False
        return warehouse_ids[0]

    def _get_shipped(self, cr, uid, ids, name, args, context=None):
        res = {}
        for sale in self.browse(cr, uid, ids, context=context):
            group = sale.procurement_group_id
            if group:
                res[sale.id] = all([proc.state in ['cancel', 'done'] for proc in group.procurement_ids])
            else:
                res[sale.id] = False
        return res

    def _get_orders(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.procurement_id and move.procurement_id.sale_line_id:
                res.add(move.procurement_id.sale_line_id.order_id.id)
        return list(res)

    def _get_orders_procurements(self, cr, uid, ids, context=None):
        res = set()
        for proc in self.pool.get('procurement.order').browse(cr, uid, ids, context=context):
            if proc.state =='done' and proc.sale_line_id:
                res.add(proc.sale_line_id.order_id.id)
        return list(res)

    def _get_picking_ids(self, cr, uid, ids, name, args, context=None):
        res = {}
        for sale in self.browse(cr, uid, ids, context=context):
            if not sale.procurement_group_id:
                res[sale.id] = []
                continue
            res[sale.id] = self.pool.get('stock.picking').search(cr, uid, [('group_id', '=', sale.procurement_group_id.id)], context=context)
        return res

    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        vals = super(sale_order, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
        location_id = order.partner_shipping_id.property_stock_customer.id
        vals['location_id'] = location_id
        routes = line.route_id and [(4, line.route_id.id)] or []
        vals['route_ids'] = routes
        vals['warehouse_id'] = order.warehouse_id and order.warehouse_id.id or False
        vals['partner_dest_id'] = order.partner_shipping_id.id
        return vals

    _columns = {
        'incoterm': fields.many2one('stock.incoterms', 'Incoterm', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
        'picking_policy': fields.selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')],
            'Shipping Policy', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""Pick 'Deliver each product when available' if you allow partial delivery."""),
        'order_policy': fields.selection([
                ('manual', 'On Demand'),
                ('picking', 'On Delivery Order'),
                ('prepaid', 'Before Delivery'),
            ], 'Create Invoice', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""On demand: A draft invoice can be created from the sales order when needed. \nOn delivery order: A draft invoice can be created from the delivery order when the products have been delivered. \nBefore delivery: A draft invoice is created from the sales order and must be paid before the products can be delivered."""),
        'shipped': fields.function(_get_shipped, string='Delivered', type='boolean', store={
                'procurement.order': (_get_orders_procurements, ['state'], 10)
            }),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking associated to this sale'),
    }
    _defaults = {
        'warehouse_id': _get_default_warehouse,
        'picking_policy': 'direct',
        'order_policy': 'manual',
    }
    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        val = {}
        if warehouse_id:
            warehouse = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
            if warehouse.company_id:
                val['company_id'] = warehouse.company_id.id
        return {'value': val}

    def action_view_delivery(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree_all')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        #compute the number of delivery orders to display
        pick_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in so.picking_ids]
            
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result

    def action_invoice_create(self, cr, uid, ids, grouped=False, states=['confirmed', 'done', 'exception'], date_invoice = False, context=None):
        move_obj = self.pool.get("stock.move")
        res = super(sale_order,self).action_invoice_create(cr, uid, ids, grouped=grouped, states=states, date_invoice = date_invoice, context=context)
        for order in self.browse(cr, uid, ids, context=context):
            if order.order_policy == 'picking':
                for picking in order.picking_ids:
                    move_obj.write(cr, uid, [x.id for x in picking.move_lines], {'invoice_state': 'invoiced'}, context=context)
        return res

    def action_wait(self, cr, uid, ids, context=None):
        res = super(sale_order, self).action_wait(cr, uid, ids, context=context)
        for o in self.browse(cr, uid, ids):
            noprod = self.test_no_product(cr, uid, o, context)
            if noprod and o.order_policy=='picking':
                self.write(cr, uid, [o.id], {'order_policy': 'manual'}, context=context)
        return res

    def _get_date_planned(self, cr, uid, order, line, start_date, context=None):
        date_planned = super(sale_order, self)._get_date_planned(cr, uid, order, line, start_date, context=context)
        date_planned = (date_planned - timedelta(days=order.company_id.security_lead)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return date_planned

    def _prepare_procurement_group(self, cr, uid, order, context=None):
        res = super(sale_order, self)._prepare_procurement_group(cr, uid, order, context=None)
        res.update({'move_type': order.picking_policy})
        return res

    def action_ship_end(self, cr, uid, ids, context=None):
        super(sale_order, self).action_ship_end(cr, uid, ids, context=context)
        for order in self.browse(cr, uid, ids, context=context):
            val = {'shipped': True}
            if order.state == 'shipping_except':
                val['state'] = 'progress'
                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
            res = self.write(cr, uid, [order.id], val)
        return True

    def has_stockable_products(self, cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.state == 'cancel':
                    continue
                if order_line.product_id and order_line.product_id.type in ('product', 'consu'):
                    return True
        return False


class product_product(osv.osv):
    _inherit = 'product.product'
    
    def need_procurement(self, cr, uid, ids, context=None):
        #when sale/product is installed alone, there is no need to create procurements, but with sale_stock
        #we must create a procurement for each product that is not a service.
        for product in self.browse(cr, uid, ids, context=context):
            if product.id and product.type != 'service':
                return True
        return super(product_product, self).need_procurement(cr, uid, ids, context=context)

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'


    def _number_packages(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            try:
                res[line.id] = int((line.product_uom_qty+line.product_packaging.qty-0.0001) / line.product_packaging.qty)
            except:
                res[line.id] = 1
        return res

    _columns = {
        'product_packaging': fields.many2one('product.packaging', 'Packaging'),
        'number_packages': fields.function(_number_packages, type='integer', string='Number Packages'),
        'route_id': fields.many2one('stock.location.route', 'Route', domain=[('sale_selectable', '=', True)]),
        'product_tmpl_id': fields.related('product_id', 'product_tmpl_id', type='many2one', relation='product.template', string='Product Template'),
    }

    _defaults = {
        'product_packaging': False,
    }

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
            warning_msgs = res.get('warning') and res['warning'].get('message', '') or ''

        products = product_obj.browse(cr, uid, product, context=context)
        if not products.packaging_ids:
            packaging = result['product_packaging'] = False

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
                       'title': _('Configuration Error!'),
                       'message': warning_msgs
                }
            result['product_uom_qty'] = qty

        return {'value': result, 'warning': warning}

    def _check_routing(self, cr, uid, ids, product, warehouse_id, context=None):
        """ Verify the route of the product based on the warehouse
            return True if the product availibility in stock does not need to be verified
        """
        is_available = False
        if warehouse_id:
            warehouse = self.pool['stock.warehouse'].browse(cr, uid, warehouse_id, context=context)
            for product_route in product.route_ids:
                if warehouse.mto_pull_id and warehouse.mto_pull_id.route_id and warehouse.mto_pull_id.route_id.id == product_route.id:
                    is_available = True
                    break
        else:
            try:
                mto_route_id = self.pool['stock.warehouse']._get_mto_route(cr, uid, context=context)
            except osv.except_osv:
                # if route MTO not found in ir_model_data, we treat the product as in MTS
                mto_route_id = False
            if mto_route_id:
                for product_route in product.route_ids:
                    if product_route.id == mto_route_id:
                        is_available = True
                        break
        return is_available

    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, context=None):
        context = context or {}
        product_uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')
        warning = {}
        #UoM False due to hack which makes sure uom changes price, ... in product_id_change
        res = self.product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=False, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)

        if not product:
            res['value'].update({'product_packaging': False})
            return res

        # set product uom in context to get virtual stock in current uom
        if 'product_uom' in res.get('value', {}):
            # use the uom changed by super call
            context = dict(context, uom=res['value']['product_uom'])
        elif uom:
            # fallback on selected
            context = dict(context, uom=uom)

        #update of result obtained in super function
        product_obj = product_obj.browse(cr, uid, product, context=context)
        res['value'].update({'product_tmpl_id': product_obj.product_tmpl_id.id, 'delay': (product_obj.sale_delay or 0.0)})

        # Calling product_packaging_change function after updating UoM
        res_packing = self.product_packaging_change(cr, uid, ids, pricelist, product, qty, uom, partner_id, packaging, context=context)
        res['value'].update(res_packing.get('value', {}))
        warning_msgs = res_packing.get('warning') and res_packing['warning']['message'] or ''

        if product_obj.type == 'product':
            #determine if the product needs further check for stock availibility
            is_available = self._check_routing(cr, uid, ids, product_obj, warehouse_id, context=context)

            #check if product is available, and if not: raise a warning, but do this only for products that aren't processed in MTO
            if not is_available:
                uom_record = False
                if uom:
                    uom_record = product_uom_obj.browse(cr, uid, uom, context=context)
                    if product_obj.uom_id.category_id.id != uom_record.category_id.id:
                        uom_record = False
                if not uom_record:
                    uom_record = product_obj.uom_id
                compare_qty = float_compare(product_obj.virtual_available, qty, precision_rounding=uom_record.rounding)
                if compare_qty == -1:
                    warn_msg = _('You plan to sell %.2f %s but you only have %.2f %s available !\nThe real stock is %.2f %s. (without reservations)') % \
                        (qty, uom_record.name,
                         max(0,product_obj.virtual_available), uom_record.name,
                         max(0,product_obj.qty_available), uom_record.name)
                    warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"

        #update of warning messages
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        res.update({'warning': warning})
        return res

    def button_cancel(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for procurement in lines.mapped('procurement_ids'):
            for move in procurement.move_ids:
                if move.state == 'done' and not move.scrapped:
                    raise osv.except_osv(_('Invalid Action!'), _('You cannot cancel a sale order line which is linked to a stock move already done.'))
        return super(sale_order_line, self).button_cancel(cr, uid, ids, context=context)

class stock_move(osv.osv):
    _inherit = 'stock.move'

    def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
        invoice_line_id = super(stock_move, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
        if context.get('inv_type') in ('out_invoice', 'out_refund') and move.procurement_id and move.procurement_id.sale_line_id:
            sale_line = move.procurement_id.sale_line_id
            self.pool.get('sale.order.line').write(cr, uid, [sale_line.id], {
                'invoice_lines': [(4, invoice_line_id)]
            }, context=context)
            self.pool.get('sale.order').write(cr, uid, [sale_line.order_id.id], {
                'invoice_ids': [(4, invoice_line_vals['invoice_id'])],
            })
            sale_line_obj = self.pool.get('sale.order.line')
            invoice_line_obj = self.pool.get('account.invoice.line')
            sale_line_ids = sale_line_obj.search(cr, uid, [('order_id', '=', move.procurement_id.sale_line_id.order_id.id), ('invoiced', '=', False), '|', ('product_id', '=', False), ('product_id.type', '=', 'service')], context=context)
            if sale_line_ids:
                created_lines = sale_line_obj.invoice_line_create(cr, uid, sale_line_ids, context=context)
                invoice_line_obj.write(cr, uid, created_lines, {'invoice_id': invoice_line_vals['invoice_id']}, context=context)

        return invoice_line_id

    def _get_master_data(self, cr, uid, move, company, context=None):
        if context.get('inv_type') in ('out_invoice', 'out_refund') and move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.order_policy == 'picking':
            sale_order = move.procurement_id.sale_line_id.order_id
            return sale_order.partner_invoice_id, sale_order.user_id.id, sale_order.pricelist_id.currency_id.id
        elif move.picking_id.sale_id and context.get('inv_type') in ('out_invoice', 'out_refund'):
            # In case of extra move, it is better to use the same data as the original moves
            sale_order = move.picking_id.sale_id
            return sale_order.partner_invoice_id, sale_order.user_id.id, sale_order.pricelist_id.currency_id.id
        return super(stock_move, self)._get_master_data(cr, uid, move, company, context=context)

    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
        if inv_type in ('out_invoice', 'out_refund') and move.procurement_id and move.procurement_id.sale_line_id:
            sale_line = move.procurement_id.sale_line_id
            res['invoice_line_tax_id'] = [(6, 0, [x.id for x in sale_line.tax_id])]
            res['account_analytic_id'] = sale_line.order_id.project_id and sale_line.order_id.project_id.id or False
            res['discount'] = sale_line.discount
            if move.product_id.id != sale_line.product_id.id:
                res['price_unit'] = self.pool['product.pricelist'].price_get(
                    cr, uid, [sale_line.order_id.pricelist_id.id],
                    move.product_id.id, move.product_uom_qty or 1.0,
                    sale_line.order_id.partner_id, context=context)[sale_line.order_id.pricelist_id.id]
            else:
                res['price_unit'] = sale_line.price_unit
            uos_coeff = move.product_uom_qty and move.product_uos_qty / move.product_uom_qty or 1.0
            res['price_unit'] = res['price_unit'] / uos_coeff
        return res

    def _get_moves_taxes(self, cr, uid, moves, inv_type, context=None):
        is_extra_move, extra_move_tax = super(stock_move, self)._get_moves_taxes(cr, uid, moves, inv_type, context=context)
        if inv_type == 'out_invoice':
            for move in moves:
                if move.procurement_id and move.procurement_id.sale_line_id:
                    is_extra_move[move.id] = False
                    extra_move_tax[move.picking_id, move.product_id] = [(6, 0, [x.id for x in move.procurement_id.sale_line_id.tax_id])]
                elif move.picking_id.sale_id and move.product_id.product_tmpl_id.taxes_id:
                    fp = move.picking_id.sale_id.fiscal_position
                    res = self.pool.get("account.invoice.line").product_id_change(cr, uid, [], move.product_id.id, None, partner_id=move.picking_id.partner_id.id, fposition_id=(fp and fp.id), context=context)
                    extra_move_tax[0, move.product_id] = [(6, 0, res['value']['invoice_line_tax_id'])]
                else:
                    extra_move_tax[0, move.product_id] = [(6, 0, [x.id for x in move.product_id.product_tmpl_id.taxes_id])]
        return (is_extra_move, extra_move_tax)

    def _get_taxes(self, cr, uid, move, context=None):
        if move.procurement_id.sale_line_id.tax_id:
            return [tax.id for tax in move.procurement_id.sale_line_id.tax_id]
        return super(stock_move, self)._get_taxes(cr, uid, move, context=context)

class stock_location_route(osv.osv):
    _inherit = "stock.location.route"
    _columns = {
        'sale_selectable': fields.boolean("Selectable on Sales Order Line")
        }


class stock_picking(osv.osv):
    _inherit = "stock.picking"

    def _get_partner_to_invoice(self, cr, uid, picking, context=None):
        """ Inherit the original function of the 'stock' module
            We select the partner of the sales order as the partner of the customer invoice
        """
        if picking.sale_id:
            saleorder_ids = self.pool['sale.order'].search(cr, uid, [('procurement_group_id' ,'=', picking.group_id.id)], context=context)
            saleorders = self.pool['sale.order'].browse(cr, uid, saleorder_ids, context=context)
            if saleorders and saleorders[0] and saleorders[0].order_policy == 'picking':
                saleorder = saleorders[0]
                return saleorder.partner_invoice_id.id
        return super(stock_picking, self)._get_partner_to_invoice(cr, uid, picking, context=context)
    
    def _get_sale_id(self, cr, uid, ids, name, args, context=None):
        sale_obj = self.pool.get("sale.order")
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            if picking.group_id:
                sale_ids = sale_obj.search(cr, uid, [('procurement_group_id', '=', picking.group_id.id)], context=context)
                if sale_ids:
                    res[picking.id] = sale_ids[0]
        return res
    
    _columns = {
        'sale_id': fields.function(_get_sale_id, type="many2one", relation="sale.order", string="Sale Order"),
    }

    def _create_invoice_from_picking(self, cr, uid, picking, vals, context=None):
        sale_obj = self.pool.get('sale.order')
        sale_line_obj = self.pool.get('sale.order.line')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_id = super(stock_picking, self)._create_invoice_from_picking(cr, uid, picking, vals, context=context)
        return invoice_id

    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        inv_vals = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
        sale = move.picking_id.sale_id
        if sale:
            inv_vals.update({
                'fiscal_position': sale.fiscal_position.id,
                'payment_term': sale.payment_term.id,
                'user_id': sale.user_id.id,
                'section_id': sale.section_id.id,
                'name': sale.client_order_ref or '',
                'comment': sale.note,
                })
        return inv_vals
