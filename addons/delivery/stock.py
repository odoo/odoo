# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import netsvc
from osv import fields,osv
from tools.translate import _

# Overloaded stock_picking to manage carriers :
class stock_picking(osv.osv):
    _name = "stock.picking"
    _description = "Picking list"
    _inherit = 'stock.picking'
    _columns = {
        'carrier_id':fields.many2one("delivery.carrier","Carrier"),
        'volume': fields.float('Volume'),
        'weight': fields.float('Weight'),
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

