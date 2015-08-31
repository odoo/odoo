# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        return super(res_partner, self)._commercial_fields(cr, uid, context=context)

    _columns = {
        'property_purchase_currency_id': fields.property(
            type='many2one',
            relation='res.currency',
            string="Supplier Currency",
            help="This currency will be used, instead of the default one, for purchases from the current partner"),
        'purchase_order_count': fields.function(_purchase_invoice_count, string='# of Purchase Order', type='integer', multi="count"),
        'supplier_invoice_count': fields.function(_purchase_invoice_count, string='# Vendor Bills', type='integer', multi="count"),
    }
