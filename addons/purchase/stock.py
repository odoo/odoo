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

from osv import osv, fields

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'purchase_line_id': fields.many2one('purchase.order.line',
            'Purchase Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    def _get_reference_accounting_values_for_valuation(self, cr, uid, move, context=None):
        """
        Overrides the default stock valuation to take into account the currency that was specified
        on the purchase order in case the valuation data was not directly specified during picking
        confirmation.
        """
        product_uom_obj = self.pool.get('product.uom')

        reference_amount, reference_currency_id = super(stock_move, self)._get_reference_accounting_values_for_valuation(cr, uid, move, context=context)
        default_uom = move.product_id.uom_id.id
        qty = product_uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, default_uom)
        if move.product_id.cost_method != 'average' or not move.price_unit:
            # no average price costing or cost not specified during picking validation, we will
            # plug the purchase line values if they are found.
            if move.purchase_line_id and move.picking_id.purchase_id.pricelist_id:
                reference_amount, reference_currency_id = move.purchase_line_id.price_unit * qty, move.picking_id.purchase_id.pricelist_id.currency_id.id
        return reference_amount, reference_currency_id

stock_move()

#
# Inherit of picking to add the link to the PO
#
class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
        'purchase_id': fields.many2one('purchase.order', 'Purchase Order',
            ondelete='set null', select=True),
    }
    _defaults = {
        'purchase_id': False,
    }

    def _get_address_invoice(self, cr, uid, picking):
        """ Gets invoice address of a partner
        @return {'contact': address, 'invoice': address} for invoice
        """
        res = super(stock_picking, self)._get_address_invoice(cr, uid, picking)
        if picking.purchase_id:
            partner_obj = self.pool.get('res.partner')
            partner = picking.purchase_id.partner_id or picking.address_id.partner_id
            data = partner_obj.address_get(cr, uid, [partner.id],
                ['contact', 'invoice'])
            res.update(data)
        return res

    def get_currency_id(self, cursor, user, picking):
        if picking.purchase_id:
            return picking.purchase_id.pricelist_id.currency_id.id
        else:
            return super(stock_picking, self).get_currency_id(cursor, user, picking)

    def _get_comment_invoice(self, cursor, user, picking):
        if picking.purchase_id and picking.purchase_id.notes:
            if picking.note:
                return picking.note + '\n' + picking.purchase_id.notes
            else:
                return picking.purchase_id.notes
        return super(stock_picking, self)._get_comment_invoice(cursor, user, picking)

    def _get_price_unit_invoice(self, cursor, user, move_line, type):
        if move_line.purchase_line_id:
            if move_line.purchase_line_id.order_id.invoice_method == 'picking':
                return move_line.price_unit
            else:
                return move_line.purchase_line_id.price_unit
        return super(stock_picking, self)._get_price_unit_invoice(cursor, user, move_line, type)

    def _get_discount_invoice(self, cursor, user, move_line):
        if move_line.purchase_line_id:
            return 0.0
        return super(stock_picking, self)._get_discount_invoice(cursor, user, move_line)

    def _get_taxes_invoice(self, cursor, user, move_line, type):
        if move_line.purchase_line_id:
            return [x.id for x in move_line.purchase_line_id.taxes_id]
        return super(stock_picking, self)._get_taxes_invoice(cursor, user, move_line, type)

    def _get_account_analytic_invoice(self, cursor, user, picking, move_line):
        if picking.purchase_id and move_line.purchase_line_id:
            return move_line.purchase_line_id.account_analytic_id.id
        return super(stock_picking, self)._get_account_analytic_invoice(cursor, user, picking, move_line)

    def _invoice_line_hook(self, cursor, user, move_line, invoice_line_id):
        if move_line.purchase_line_id:
            invoice_line_obj = self.pool.get('account.invoice.line')
            invoice_line_obj.write(cursor, user, [invoice_line_id], {'note':  move_line.purchase_line_id.notes,})
        return super(stock_picking, self)._invoice_line_hook(cursor, user, move_line, invoice_line_id)

    def _invoice_hook(self, cursor, user, picking, invoice_id):
        purchase_obj = self.pool.get('purchase.order')
        if picking.purchase_id:
            purchase_obj.write(cursor, user, [picking.purchase_id.id], {'invoice_id': invoice_id,})
        return super(stock_picking, self)._invoice_hook(cursor, user, picking, invoice_id)

class stock_partial_picking(osv.osv_memory):
    _inherit = 'stock.partial.picking'

    # Overridden to inject the purchase price as true 'cost price' when processing
    # incoming pickings.
    def _product_cost_for_average_update(self, cr, uid, move):
        if move.picking_id.purchase_id:
            return {'cost': move.purchase_line_id.price_unit,
                    'currency': move.picking_id.purchase_id.pricelist_id.currency_id.id}
        return super(stock_partial_picking, self)._product_cost_for_average_update(cr, uid, move)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
