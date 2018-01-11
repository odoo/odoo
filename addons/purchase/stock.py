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

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'purchase_line_id': fields.many2one('purchase.order.line',
            'Purchase Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    def get_price_unit(self, cr, uid, move, context=None):
        """ Returns the unit price to store on the quant """
        if move.purchase_line_id:
            return move.price_unit

        return super(stock_move, self).get_price_unit(cr, uid, move, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        from openerp import workflow
        if vals.get('state') in ['done', 'cancel']:
            po_to_check = []
            for move in self.browse(cr, uid, ids, context=context):
                if move.purchase_line_id and move.purchase_line_id.order_id:
                    order = move.purchase_line_id.order_id
                    order_id = order.id
                    # update linked purchase order as superuser as the warehouse
                    # user may not have rights to access purchase.order
                    if self.pool.get('purchase.order').test_moves_done(cr, uid, [order_id], context=context):
                        workflow.trg_validate(SUPERUSER_ID, 'purchase.order', order_id, 'picking_done', cr)
                    if self.pool.get('purchase.order').test_moves_except(cr, uid, [order_id], context=context):
                        workflow.trg_validate(SUPERUSER_ID, 'purchase.order', order_id, 'picking_cancel', cr)
                    if order_id not in po_to_check and vals['state'] == 'cancel' and order.invoice_method == 'picking':
                        po_to_check.append(order_id)
            # Some moves which are cancelled might be part of a PO line which is partially
            # invoiced, so we check if some PO line can be set on "invoiced = True".
            if po_to_check:
                self.pool.get('purchase.order')._set_po_lines_invoiced(cr, uid, po_to_check, context=context)
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        context = context or {}
        if not default.get('split_from'):
            #we don't want to propagate the link to the purchase order line except in case of move split
            default['purchase_line_id'] = False
        return super(stock_move, self).copy(cr, uid, id, default, context)

    def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
        if move.purchase_line_id:
            invoice_line_vals['purchase_line_id'] = move.purchase_line_id.id
            invoice_line_vals['account_analytic_id'] = move.purchase_line_id.account_analytic_id.id or False
        invoice_line_id = super(stock_move, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
        if context.get('inv_type') in ('in_invoice', 'in_refund') and move.purchase_line_id:
            purchase_line = move.purchase_line_id
            self.pool.get('purchase.order.line').write(cr, uid, [purchase_line.id], {
                'invoice_lines': [(4, invoice_line_id)]
            }, context=context)
            self.pool.get('purchase.order').write(cr, uid, [purchase_line.order_id.id], {
                'invoice_ids': [(4, invoice_line_vals['invoice_id'])],
            })
            purchase_line_obj = self.pool.get('purchase.order.line')
            purchase_obj = self.pool.get('purchase.order')
            invoice_line_obj = self.pool.get('account.invoice.line')
            purchase_id = move.purchase_line_id.order_id.id
            purchase_line_ids = purchase_line_obj.search(cr, uid, [('order_id', '=', purchase_id), ('invoice_lines', '=', False), '|', ('product_id', '=', False), ('product_id.type', '=', 'service')], context=context)
            if purchase_line_ids:
                inv_lines = []
                for po_line in purchase_line_obj.browse(cr, uid, purchase_line_ids, context=context):
                    acc_id = purchase_obj._choose_account_from_po_line(cr, uid, po_line, context=context)
                    inv_line_data = purchase_obj._prepare_inv_line(cr, uid, acc_id, po_line, context=context)
                    inv_line_id = invoice_line_obj.create(cr, uid, inv_line_data, context=context)
                    inv_lines.append(inv_line_id)
                    po_line.write({'invoice_lines': [(4, inv_line_id)]})
                invoice_line_obj.write(cr, uid, inv_lines, {'invoice_id': invoice_line_vals['invoice_id']}, context=context)
        return invoice_line_id

    def _get_master_data(self, cr, uid, move, company, context=None):
        if context.get('inv_type') == 'in_invoice' and move.purchase_line_id:
            purchase_order = move.purchase_line_id.order_id
            return purchase_order.partner_id, purchase_order.create_uid.id, purchase_order.currency_id.id
        if context.get('inv_type') == 'in_refund' and move.origin_returned_move_id.purchase_line_id:
            purchase_order = move.origin_returned_move_id.purchase_line_id.order_id
            return purchase_order.partner_id, purchase_order.create_uid.id, purchase_order.currency_id.id
        elif context.get('inv_type') in ('in_invoice', 'in_refund') and move.picking_id:
            # In case of an extra move, it is better to use the data from the original moves
            for purchase_move in move.picking_id.move_lines:
                if purchase_move.purchase_line_id:
                    purchase_order = purchase_move.purchase_line_id.order_id
                    return purchase_order.partner_id, purchase_order.create_uid.id, purchase_order.currency_id.id

            partner = move.picking_id and move.picking_id.partner_id or False
            code = self.get_code_from_locs(cr, uid, move, context=context)
            if partner and partner.property_product_pricelist_purchase and code == 'incoming':
                currency = partner.property_product_pricelist_purchase.currency_id.id
                return partner, uid, currency
        return super(stock_move, self)._get_master_data(cr, uid, move, company, context=context)


    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
        if inv_type == 'in_invoice' and move.purchase_line_id:
            purchase_line = move.purchase_line_id
            res['invoice_line_tax_id'] = [(6, 0, [x.id for x in purchase_line.taxes_id])]
            res['price_unit'] = purchase_line.price_unit
        elif inv_type == 'in_refund' and move.origin_returned_move_id.purchase_line_id:
            purchase_line = move.origin_returned_move_id.purchase_line_id
            res['invoice_line_tax_id'] = [(6, 0, [x.id for x in purchase_line.taxes_id])]
            res['price_unit'] = purchase_line.price_unit
        return res

    def _get_moves_taxes(self, cr, uid, moves, inv_type, context=None):
        is_extra_move, extra_move_tax = super(stock_move, self)._get_moves_taxes(cr, uid, moves, inv_type, context=context)
        if inv_type == 'in_invoice':
            for move in moves:
                if move.purchase_line_id:
                    is_extra_move[move.id] = False
                    extra_move_tax[move.picking_id, move.product_id] = [(6, 0, [x.id for x in move.purchase_line_id.taxes_id])]
                elif move.product_id.product_tmpl_id.supplier_taxes_id:
                    mov_id = self.search(cr, uid, [('purchase_line_id', '!=', False), ('picking_id', '=', move.picking_id.id)], limit=1, context=context)
                    if mov_id:
                        mov = self.browse(cr, uid, mov_id[0], context=context)
                        fp = mov.purchase_line_id.order_id.fiscal_position
                        res = self.pool.get("account.invoice.line").product_id_change(cr, uid, [], move.product_id.id, None, partner_id=move.picking_id.partner_id.id, fposition_id=(fp and fp.id), type='in_invoice', context=context)
                        extra_move_tax[0, move.product_id] = [(6, 0, res['value']['invoice_line_tax_id'])]
        return (is_extra_move, extra_move_tax)


    def attribute_price(self, cr, uid, move, context=None):
        """
            Attribute price to move, important in inter-company moves or receipts with only one partner
        """
        # The method attribute_price of the parent class sets the price to the standard product
        # price if move.price_unit is zero. We don't want this behavior in the case of a purchase
        # order since we can purchase goods which are free of charge (e.g. 5 units offered if 100
        # are purchased).
        if move.purchase_line_id:
            return

        code = self.get_code_from_locs(cr, uid, move, context=context)
        if not move.purchase_line_id and code == 'incoming' and not move.price_unit:
            partner = move.picking_id and move.picking_id.partner_id or False
            price = False
            # If partner given, search price in its purchase pricelist
            if partner and partner.property_product_pricelist_purchase:
                pricelist_obj = self.pool.get("product.pricelist")
                pricelist = partner.property_product_pricelist_purchase.id
                price = pricelist_obj.price_get(cr, uid, [pricelist],
                                    move.product_id.id, move.product_uom_qty, partner.id, {
                                                                                'uom': move.product_uom.id,
                                                                                'date': move.date,
                                                                                })[pricelist]
                if price:
                    return self.write(cr, uid, [move.id], {'price_unit': price}, context=context)
        super(stock_move, self).attribute_price(cr, uid, move, context=context)

    def _get_taxes(self, cr, uid, move, context=None):
        if move.origin_returned_move_id.purchase_line_id.taxes_id:
            return [tax.id for tax in move.origin_returned_move_id.purchase_line_id.taxes_id]
        return super(stock_move, self)._get_taxes(cr, uid, move, context=context)

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def _get_to_invoice(self, cr, uid, ids, name, args, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            for move in picking.move_lines:
                if move.purchase_line_id and move.purchase_line_id.order_id.invoice_method == 'picking':
                    if not move.move_orig_ids:
                        res[picking.id] = True
        return res

    def _get_picking_to_recompute(self, cr, uid, ids, context=None):
        picking_ids = set()
        for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            if move.picking_id and move.purchase_line_id:
                picking_ids.add(move.picking_id.id)
        return list(picking_ids)

    _columns = {
        'reception_to_invoice': fields.function(_get_to_invoice, type='boolean', string='Invoiceable on incoming shipment?',
               help='Does the picking contains some moves related to a purchase order invoiceable on the receipt?',
               store={
                   'stock.move': (_get_picking_to_recompute, ['purchase_line_id', 'picking_id'], 10),
               }),
    }

    def _create_invoice_from_picking(self, cr, uid, picking, vals, context=None):
        purchase_obj = self.pool.get("purchase.order")
        purchase_line_obj = self.pool.get('purchase.order.line')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_id = super(stock_picking, self)._create_invoice_from_picking(cr, uid, picking, vals, context=context)
        return invoice_id

    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        inv_vals = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
        if move.purchase_line_id and move.purchase_line_id.order_id:
            purchase = move.purchase_line_id.order_id
            inv_vals.update({
                'fiscal_position': purchase.fiscal_position.id,
                'payment_term': purchase.payment_term_id.id,
                })
        return inv_vals


class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    _columns = {
        'buy_to_resupply': fields.boolean('Purchase to resupply this warehouse', 
                                          help="When products are bought, they can be delivered to this warehouse"),
        'buy_pull_id': fields.many2one('procurement.rule', 'Buy rule'),
    }
    _defaults = {
        'buy_to_resupply': True,
    }

    def _get_buy_pull_rule(self, cr, uid, warehouse, context=None):
        route_obj = self.pool.get('stock.location.route')
        data_obj = self.pool.get('ir.model.data')
        try:
            buy_route_id = data_obj.get_object_reference(cr, uid, 'purchase', 'route_warehouse0_buy')[1]
        except:
            buy_route_id = route_obj.search(cr, uid, [('name', 'like', _('Buy'))], context=context)
            buy_route_id = buy_route_id and buy_route_id[0] or False
        if not buy_route_id:
            raise osv.except_osv(_('Error!'), _('Can\'t find any generic Buy route.'))

        return {
            'name': self._format_routename(cr, uid, warehouse, _(' Buy'), context=context),
            'location_id': warehouse.in_type_id.default_location_dest_id.id,
            'route_id': buy_route_id,
            'action': 'buy',
            'picking_type_id': warehouse.in_type_id.id,
            'warehouse_id': warehouse.id,
        }

    def create_routes(self, cr, uid, ids, warehouse, context=None):
        pull_obj = self.pool.get('procurement.rule')
        res = super(stock_warehouse, self).create_routes(cr, uid, ids, warehouse, context=context)
        if warehouse.buy_to_resupply:
            buy_pull_vals = self._get_buy_pull_rule(cr, uid, warehouse, context=context)
            buy_pull_id = pull_obj.create(cr, uid, buy_pull_vals, context=context)
            res['buy_pull_id'] = buy_pull_id
        return res

    def write(self, cr, uid, ids, vals, context=None):
        pull_obj = self.pool.get('procurement.rule')
        if isinstance(ids, (int, long)):
            ids = [ids]

        if 'buy_to_resupply' in vals:
            if vals.get("buy_to_resupply"):
                for warehouse in self.browse(cr, uid, ids, context=context):
                    if not warehouse.buy_pull_id:
                        buy_pull_vals = self._get_buy_pull_rule(cr, uid, warehouse, context=context)
                        buy_pull_id = pull_obj.create(cr, uid, buy_pull_vals, context=context)
                        vals['buy_pull_id'] = buy_pull_id
            else:
                for warehouse in self.browse(cr, uid, ids, context=context):
                    if warehouse.buy_pull_id:
                        buy_pull_id = pull_obj.unlink(cr, uid, warehouse.buy_pull_id.id, context=context)
        return super(stock_warehouse, self).write(cr, uid, ids, vals, context=None)

    def get_all_routes_for_wh(self, cr, uid, warehouse, context=None):
        all_routes = super(stock_warehouse, self).get_all_routes_for_wh(cr, uid, warehouse, context=context)
        if warehouse.buy_to_resupply and warehouse.buy_pull_id and warehouse.buy_pull_id.route_id:
            all_routes += [warehouse.buy_pull_id.route_id.id]
        return all_routes

    def _get_all_products_to_resupply(self, cr, uid, warehouse, context=None):
        res = super(stock_warehouse, self)._get_all_products_to_resupply(cr, uid, warehouse, context=context)
        if warehouse.buy_pull_id and warehouse.buy_pull_id.route_id:
            for product_id in res:
                for route in self.pool.get('product.product').browse(cr, uid, product_id, context=context).route_ids:
                    if route.id == warehouse.buy_pull_id.route_id.id:
                        res.remove(product_id)
                        break
        return res

    def _handle_renaming(self, cr, uid, warehouse, name, code, context=None):
        res = super(stock_warehouse, self)._handle_renaming(cr, uid, warehouse, name, code, context=context)
        pull_obj = self.pool.get('procurement.rule')
        #change the buy pull rule name
        if warehouse.buy_pull_id:
            pull_obj.write(cr, uid, warehouse.buy_pull_id.id, {'name': warehouse.buy_pull_id.name.replace(warehouse.name, name, 1)}, context=context)
        return res

    def change_route(self, cr, uid, ids, warehouse, new_reception_step=False, new_delivery_step=False, context=None):
        res = super(stock_warehouse, self).change_route(cr, uid, ids, warehouse, new_reception_step=new_reception_step, new_delivery_step=new_delivery_step, context=context)
        if warehouse.in_type_id.default_location_dest_id != warehouse.buy_pull_id.location_id:
            self.pool.get('procurement.rule').write(cr, uid, warehouse.buy_pull_id.id, {'location_id': warehouse.in_type_id.default_location_dest_id.id}, context=context)
        return res
