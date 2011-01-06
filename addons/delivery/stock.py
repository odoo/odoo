# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import netsvc
from osv import fields,osv
from tools.translate import _
import tools

# Overloaded stock_picking to manage carriers :
class stock_picking(osv.osv):
    _name = "stock.picking"
    _description = "Picking list"
    _inherit = 'stock.picking'

    def _cal_weight(self, cr, uid, ids, name, args, context=None):
        res = {}
        uom_obj = self.pool.get('product.uom')
        for picking in self.browse(cr, uid, ids, context):
            total_weight = 0.00
            for move in picking.move_lines:
                weight = 0.00
                if move.product_id.weight > 0.00:
                    converted_qty = move.product_qty
#                    from_uom = move.product_uom.id
#                    pass_qty = move.product_qty
#                    to_uom = move.product_id.uom_id.id
#                    if picking.type == 'out':
#                        if move.product_uos:
#                            converted_qty = move.product_uos_qty
#                            if move.product_uos.id <> move.product_uom.id:
#                                converted_qty = (move.product_uos_qty/move.product_id.uos_coeff)
#                            pass_qty = converted_qty
                    if move.product_uom.id <> move.product_id.uom_id.id:
                        converted_qty = uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, move.product_id.uom_id.id)

                    weight = (converted_qty * move.product_id.weight)
                    total_weight += weight
            res[picking.id] = total_weight
        return res

    def _get_picking_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[line.picking_id.id] = True
        return result.keys()
    
    _columns = {
        'carrier_id':fields.many2one("delivery.carrier","Carrier"),
        'volume': fields.float('Volume'),
        'weight': fields.function(_cal_weight, method=True, type='float', string='Weight',digits=(16, 6),
                  store={
                 'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 20),
                 'stock.move': (_get_picking_line, ['product_id','product_qty','product_uom','product_uos_qty'], 20),
                 }),
        }

    def action_invoice_create(self, cursor, user, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        picking_obj = self.pool.get('stock.picking')
        carrier_obj = self.pool.get('delivery.carrier')
        grid_obj = self.pool.get('delivery.grid')
        invoice_line_obj = self.pool.get('account.invoice.line')

        result = super(stock_picking, self).action_invoice_create(cursor, user,
                ids, journal_id=journal_id, group=group, type=type,
                context=context)

        picking_ids = result.keys()
        invoice_ids = result.values()

        invoices = {}
        for invoice in invoice_obj.browse(cursor, user, invoice_ids,
                context=context):
            invoices[invoice.id] = invoice

        for picking in picking_obj.browse(cursor, user, picking_ids,
                context=context):
            if not picking.carrier_id:
                continue
            grid_id = carrier_obj.grid_get(cursor, user, [picking.carrier_id.id],
                    picking.address_id.id, context=context)
            if not grid_id:
                raise osv.except_osv(_('Warning'),
                        _('The carrier %s (id: %d) has no delivery grid!') \
                                % (picking.carrier_id.name,
                                    picking.carrier_id.id))
            invoice = invoices[result[picking.id]]
            price = grid_obj.get_price_from_picking(cursor, user, grid_id,
                    invoice.amount_untaxed, picking.weight, picking.volume,
                    context=context)
            account_id = picking.carrier_id.product_id.product_tmpl_id\
                    .property_account_income.id
            if not account_id:
                account_id = picking.carrier_id.product_id.categ_id\
                        .property_account_income_categ.id

            taxes = picking.carrier_id.product_id.taxes_id

            partner_id=picking.address_id.partner_id and picking.address_id.partner_id.id or False
            taxes_ids = [x.id for x in picking.carrier_id.product_id.taxes_id]
            if partner_id:
                partner = picking.address_id.partner_id
                account_id = self.pool.get('account.fiscal.position').map_account(cursor, user, partner.property_account_position, account_id)
                taxes_ids = self.pool.get('account.fiscal.position').map_tax(cursor, user, partner.property_account_position, taxes)

            invoice_line_obj.create(cursor, user, {
                'name': picking.carrier_id.name,
                'invoice_id': invoice.id,
                'uos_id': picking.carrier_id.product_id.uos_id.id,
                'product_id': picking.carrier_id.product_id.id,
                'account_id': account_id,
                'price_unit': price,
                'quantity': 1,
                'invoice_line_tax_id': [(6, 0,taxes_ids)],
            })
        return result

stock_picking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

