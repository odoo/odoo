# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def _purchase_invoice_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict([(id, {'purchase_order_count': 0, 'supplier_invoice_count': 0}) for id in ids])
        purchase_data = self.pool['purchase.order'].read_group(cr, uid, [('partner_id', 'child_of', ids)], ['partner_id'], ['partner_id'], context=context)
        for purchase in purchase_data:
            partner_id = purchase['partner_id'][0]
            res[partner_id]['purchase_order_count'] = purchase['partner_id_count']
        invoice_data = self.pool['account.invoice'].read_group(cr, uid, [('partner_id', 'child_of', ids), ('type','=','in_invoice')], ['partner_id'], ['partner_id'], context=context)
        for invoice in invoice_data:
            partner_id = invoice['partner_id'][0]
            res[partner_id]['supplier_invoice_count'] = invoice['partner_id_count']
        return res

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
