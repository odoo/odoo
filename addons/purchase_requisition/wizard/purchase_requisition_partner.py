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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from osv import fields, osv
from osv.orm import browse_record, browse_null
from tools.translate import _

class purchase_requisition_partner(osv.osv_memory):
    _name = "purchase.requisition.partner"
    _description = "Purchase Requisition Partner"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', required=True,domain=[('supplier', '=', True)]),
        'partner_address_id':fields.many2one('res.partner.address', 'Address', required=True),
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(purchase_requisition_partner, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False) or False
        tender = self.pool.get('purchase.requisition').browse(cr, uid, record_id, context=context)
        if not tender.line_ids:
            raise osv.except_osv(_('Error!'), _('No Product in Tender'))
        True

    def onchange_partner_id(self, cr, uid, ids, partner_id):
        if not partner_id:
            return {}
        addr = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['default'])
        part = self.pool.get('res.partner').browse(cr, uid, partner_id)
        return {'value':{'partner_address_id': addr['default']}}

    def create_order(self, cr, uid, ids, context=None):
        """
             To Create a purchase orders .

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs
             @param context: A standard dictionary
             @return: {}

        """
        if context is None:
            context = {}
        record_ids = context and context.get('active_ids', False)
        if record_ids:
            data =  self.browse(cr, uid, ids,context=context)[0]
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
            order_obj = self.pool.get('purchase.order')
            order_line_obj = self.pool.get('purchase.order.line')
            partner_obj = self.pool.get('res.partner')
            tender_line_obj = self.pool.get('purchase.requisition.line')
            pricelist_obj = self.pool.get('product.pricelist')
            prod_obj = self.pool.get('product.product')
            tender_obj = self.pool.get('purchase.requisition')
            acc_pos_obj = self.pool.get('account.fiscal.position')
            partner_id = data.partner_id.id
            supplier_data = data.partner_id
            address_id = partner_obj.address_get(cr, uid, [partner_id], ['delivery'])['delivery']
            list_line=[]
            purchase_order_line={}
            for tender in tender_obj.browse(cr, uid, record_ids, context=context):
                for line in tender.line_ids:
                    partner_list = sorted([(partner.sequence, partner) for partner in  line.product_id.seller_ids if partner])
                    partner_rec = partner_list and partner_list[0] and partner_list[0][1] or False
                    uom_id = line.product_id.uom_po_id and line.product_id.uom_po_id.id or False

                    if tender.date_start:
                        newdate = datetime.strptime(tender.date_start, '%Y-%m-%d %H:%M:%S') - relativedelta(days=company.po_lead)
                    else:
                        newdate = datetime.today() - relativedelta(days=company.po_lead)
                    delay = partner_rec and partner_rec.delay or 0.0
                    if delay:
                        newdate -= relativedelta(days=delay)

                    partner = partner_rec and partner_rec.name or supplier_data
                    pricelist_id = partner.property_product_pricelist_purchase and partner.property_product_pricelist_purchase.id or False
                    price = pricelist_obj.price_get(cr, uid, [pricelist_id], line.product_id.id, line.product_qty, False, {'uom': uom_id})[pricelist_id]
                    product = prod_obj.browse(cr, uid, line.product_id.id, context=context)
                    location_id = self.pool.get('stock.warehouse').read(cr, uid, [tender.warehouse_id.id], ['lot_input_id'])[0]['lot_input_id'][0]

                    purchase_order_line= {
                            'name': product.partner_ref,
                            'product_qty': line.product_qty,
                            'product_id': line.product_id.id,
                            'product_uom': uom_id,
                            'price_unit': price,
                            'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                            'notes': product.description_purchase,
                    }
                    taxes_ids = line.product_id.product_tmpl_id.supplier_taxes_id
                    taxes = acc_pos_obj.map_tax(cr, uid, partner.property_account_position, taxes_ids)
                    purchase_order_line.update({
                            'taxes_id': [(6,0,taxes)]
                        })
                    list_line.append(purchase_order_line)
                purchase_id = order_obj.create(cr, uid, {
                            'origin': tender.purchase_ids and tender.purchase_ids[0].origin or tender.name,
                            'partner_id': partner_id,
                            'partner_address_id': address_id,
                            'pricelist_id': pricelist_id,
                            'location_id': tender.purchase_ids and tender.purchase_ids[0].location_id.id or line.product_id.product_tmpl_id.property_stock_production.id,
                            'company_id': tender.company_id.id,
                            'fiscal_position': partner.property_account_position and partner.property_account_position.id or False,
                            'requisition_id':tender.id,
                            'notes':tender.description,
                            'warehouse_id':tender.warehouse_id.id and tender.warehouse_id.id ,
                            'location_id':location_id,
                            'company_id':tender.company_id.id,
                })
                order_ids=[]
                for order_line in list_line:
                    order_line.update({
                            'order_id': purchase_id
                        })
                    order_line_obj.create(cr,uid,order_line)
        return {'type': 'ir.actions.act_window_close'}

purchase_requisition_partner()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
