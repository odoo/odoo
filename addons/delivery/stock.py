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
        for picking in self.browse(cr, uid, ids, context=context):
            total_weight = total_weight_net = 0.00

            for move in picking.move_lines:
                if move.state != 'cancel':
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
        'volume': fields.float('Volume', copy=False),
        'weight': fields.function(_cal_weight, type='float', string='Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_weight',
                  store={
                 'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 40),
                 'stock.move': (_get_picking_line, ['state', 'picking_id', 'product_id','product_uom_qty','product_uom'], 40),
                 }),
        'weight_net': fields.function(_cal_weight, type='float', string='Net Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_weight',
                  store={
                 'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 40),
                 'stock.move': (_get_picking_line, ['state', 'picking_id', 'product_id','product_uom_qty','product_uom'], 40),
                 }),
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', copy=False),
        'number_of_packages': fields.integer('Number of Packages', copy=False),
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
        if picking.sale_id:
            delivery_line = picking.sale_id.order_line.filtered(lambda l: l.is_delivery and l.invoiced)
            if delivery_line:
                return None
        carrier_obj = self.pool.get('delivery.carrier')
        grid_obj = self.pool.get('delivery.grid')
        currency_obj = self.pool.get('res.currency')
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
        quantity = sum([line.product_uom_qty for line in picking.move_lines])
        price = grid_obj.get_price_from_picking(cr, uid, grid_id,
                invoice.amount_untaxed, picking.weight, picking.volume,
                quantity, context=context)
        if invoice.company_id.currency_id.id != invoice.currency_id.id:
            price = currency_obj.compute(cr, uid, invoice.company_id.currency_id.id, invoice.currency_id.id,
                price, context=dict(context or {}, date=invoice.date_invoice))
        account_id = picking.carrier_id.product_id.property_account_income.id
        if not account_id:
            account_id = picking.carrier_id.product_id.categ_id\
                    .property_account_income_categ.id

        taxes = picking.carrier_id.product_id.taxes_id
        partner = picking.partner_id or False
        fp = invoice.fiscal_position or partner.property_account_position
        if partner:
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fp, account_id)
            taxes_ids = self.pool.get('account.fiscal.position').map_tax(cr, uid, fp, taxes, context=context)
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

    def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_ids = super(stock_picking, self)._invoice_create_line(cr, uid, moves, journal_id, inv_type=inv_type, context=context)
        delivey_invoices = {}
        for move in moves:
            for invoice in move.picking_id.sale_id.invoice_ids:
                if invoice.id in invoice_ids:
                    delivey_invoices[invoice] = move.picking_id
        if delivey_invoices:
            for invoice, picking in delivey_invoices.items():
                invoice_line = self._prepare_shipping_invoice_line(cr, uid, picking, invoice, context=context)
                if invoice_line:
                    invoice_line_obj.create(cr, uid, invoice_line)
                    invoice_obj.button_compute(cr, uid, [invoice.id], context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoice_ids

    def _get_default_uom(self, cr, uid, context=None):
        uom_categ_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'product.product_uom_categ_kgm')
        return self.pool.get('product.uom').search(cr, uid, [('category_id', '=', uom_categ_id), ('factor', '=', 1)])[0]

    _defaults = {
        'weight_uom_id': lambda self, cr, uid, c: self._get_default_uom(cr, uid, c),
    }


class stock_move(osv.osv):
    _inherit = 'stock.move'

    def _cal_move_weight(self, cr, uid, ids, name, args, context=None):
        res = {}
        uom_obj = self.pool.get('product.uom')
        for move in self.browse(cr, uid, ids, context=context):
            weight = weight_net = 0.00
            if move.product_id.weight > 0.00:
                converted_qty = move.product_qty
                weight = (converted_qty * move.product_id.weight)

                if move.product_id.weight_net > 0.00:
                    weight_net = (converted_qty * move.product_id.weight_net)

            res[move.id] =  {
                            'weight': weight,
                            'weight_net': weight_net,
                            }
        return res

    _columns = {
        'weight': fields.function(_cal_move_weight, type='float', string='Weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_move_weight',
                  store={
                 'stock.move': (lambda self, cr, uid, ids, c=None: ids, ['product_id', 'product_uom_qty', 'product_uom'], 30),
                 }),
        'weight_net': fields.function(_cal_move_weight, type='float', string='Net weight', digits_compute= dp.get_precision('Stock Weight'), multi='_cal_move_weight',
                  store={
                 'stock.move': (lambda self, cr, uid, ids, c=None: ids, ['product_id', 'product_uom_qty', 'product_uom'], 30),
                 }),
        'weight_uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True,readonly="1",help="Unit of Measure (Unit of Measure) is the unit of measurement for Weight",),
        }

    def action_confirm(self, cr, uid, ids, context=None):
        """
            Pass the carrier to the picking from the sales order
            (Should also work in case of Phantom BoMs when on explosion the original move is deleted)
        """
        procs_to_check = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.carrier_id:
                procs_to_check += [move.procurement_id]
        res = super(stock_move, self).action_confirm(cr, uid, ids, context=context)
        pick_obj = self.pool.get("stock.picking")
        for proc in procs_to_check:
            pickings = list(set([x.picking_id.id for x in proc.move_ids if x.picking_id and not x.picking_id.carrier_id]))
            if pickings:
                pick_obj.write(cr, uid, pickings, {'carrier_id': proc.sale_line_id.order_id.carrier_id.id}, context=context)
        return res


    def _get_default_uom(self, cr, uid, context=None):
        uom_categ_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'product.product_uom_categ_kgm')
        return self.pool.get('product.uom').search(cr, uid, [('category_id', '=', uom_categ_id),('factor','=',1)])[0]

    _defaults = {
        'weight_uom_id': lambda self, cr, uid, c: self._get_default_uom(cr, uid, c),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
