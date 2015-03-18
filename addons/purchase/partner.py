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

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def _purchase_invoice_count(self, cr, uid, ids, field_name, arg, context=None):
        PurchaseOrder = self.pool['purchase.order']
        Invoice = self.pool['account.invoice']
        return {
            partner_id: {
                'purchase_order_count': PurchaseOrder.search_count(cr,uid, [('partner_id', 'child_of', partner_id)], context=context),
                'supplier_invoice_count': Invoice.search_count(cr,uid, [('partner_id', 'child_of', partner_id), ('type','=','in_invoice')], context=context)
            }
            for partner_id in ids
        }

    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(cr, uid, context=context) + ['property_product_pricelist_purchase']

    _columns = {
        'property_product_pricelist_purchase': fields.property(
          type='many2one', 
          relation='product.pricelist', 
          domain=[('type','=','purchase')],
          string="Purchase Pricelist", 
          help="This pricelist will be used, instead of the default one, for purchases from the current partner"),
        'purchase_order_count': fields.function(_purchase_invoice_count, string='# of Purchase Order', type='integer', multi="count"),
        'supplier_invoice_count': fields.function(_purchase_invoice_count, string='# Supplier Invoices', type='integer', multi="count"),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

