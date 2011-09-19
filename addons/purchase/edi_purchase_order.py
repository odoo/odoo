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

from osv import fields, osv, orm
from base.ir import ir_edi
from tools.translate import _
from datetime import date, datetime, timedelta

class purchase_order(osv.osv, ir_edi.edi):
    _inherit = 'purchase.order'
    
    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Exports a purchase order"""
        edi_struct = {
            'company_id': True, # -> to be changed into partner
            'name': True,
            'partner_ref': True,
            'origin': True,
            'date_order': True,
            'partner_id': True,
            'partner_address_id': True, #only one address needed
                    #SO: 'partner_order_id'
                    #PO: 'partner_address_id'

            'pricelist_id': True,
            'notes': True,
                    #SO: 'note'
                    #PO: 'notes'
    
            'amount_total': True,
            'amount_tax': True,
            'amount_untaxed': True,
            'order_line': {
                'name': True,
                'date_planned': True,
                        #SO: 'delay' : 'date_order' - 'date_planned'
                        #PO: 'date_planned': 'date_order' + 'delay'

                'product_id': True,
                'product_uom': True,
                'price_unit': True,
                'price_subtotal': True,
                'product_qty': True,
                        #SO: 'product_uom_qty'
                        #PO: 'product_qty'

                'notes': True,
            }
        }
        company_pool = self.pool.get('res.company')
        edi_doc_list = []
        for order in records:
            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(purchase_order,self).edi_export(cr, uid, [order], edi_struct, context)
            if not edi_doc:
                continue
            edi_doc = edi_doc[0]

            # Add company info and address
            edi_company_document = company_pool.edi_export_address(cr, uid, [order.company_id], context=context)[order.company_id.id]
            edi_doc.update({
                    'company_address': edi_company_document['company_address'],
                    'currency_id': edi_company_document['currency_id'],
                    #'company_logo': edi_company_document['company_logo'],#TODO
            })
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def edi_import_company(self, cr, uid, edi_document, context=None):
        partner_address_pool = self.pool.get('res.partner.address')
        partner_pool = self.pool.get('res.partner')
        company_pool = self.pool.get('res.company')

        # import company as a new partner, supplier=1.
        # company_address data used to add address to new partner
        partner_value = {'customer': True}
        partner_id = company_pool.edi_import_as_partner(cr, uid, edi_document, values=partner_value, context=context)


        # partner_id field is modified to point to the new partner
        res = partner_pool.address_get(cr, uid, [partner_id], ['contact', 'invoice'])
        address_id = res['invoice']
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        partner_address = partner_address_pool.browse(cr, uid, address_id, context=context)
        edi_document['partner_id'] = self.edi_m2o(cr, uid, partner, context=context)
        edi_document['partner_address_id'] = self.edi_m2o(cr, uid, partner_address, context=context)
        del edi_document['company_id']
        return partner_id

    def edi_get_pricelist(self, cr, uid, partner_id, context=None):
        # return value = ["724f93ec-ddd0-11e0-88ec-701a04e25543:product.list0", "Public Pricelist (EUR)"]
        partner_model = self.pool.get('res.partner')
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        pricelist = partner.property_product_pricelist_purchase
        if not pricelist:
            pricelist = self.pool.get('ir.model.data').get_object(cr, uid, 'purchase', 'list0', context=context)
        return self.edi_m2o(cr, uid, pricelist, context=context)

    def edi_get_location(self, cr, uid, partner_id, context=None):
        # return value = ["724f93ec-ddd0-11e0-88ec-701a04e25543:stock.stock_location_stock", "Stock"]
        partner_model = self.pool.get('res.partner')
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        location = partner.property_stock_customer
        if not location:
            location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_stock', context=context)
        return self.edi_m2o(cr, uid, location, context=context)

    def edi_import(self, cr, uid, edi_document, context=None):
        if context is None:
            context = {}
        
        #import company as a new partner
        partner_id = self.edi_import_company(cr, uid, edi_document, context=context)
        
        edi_document['partner_ref'] = edi_document['name']
        edi_document['notes'] = edi_document.get('note', False)
        edi_document['pricelist_id'] = self.edi_get_pricelist(cr, uid, partner_id, context=context)
        edi_document['location_id'] = self.edi_get_location(cr, uid, partner_id, context=context)
        for order_line in edi_document['order_line']:
            order_line['product_qty'] = order_line['product_uom_qty']
            date_order = datetime.strptime(edi_document['date_order'], "%Y-%m-%d")
            delay = order_line.get('delay', 0.0)
            order_line['date_planned'] = (date_order + timedelta(days=delay)).strftime("%Y-%m-%d")
            # price_unit = price_unit - discount
            discount = order_line.get('discount', 0.0)
            price_unit = order_line['price_unit']
            if discount:
                price_unit = price_unit * (1 - (discount or 0.0) / 100.0)
            order_line['price_unit'] = price_unit
        
        return super(purchase_order,self).edi_import(cr, uid, edi_document, context=context)
purchase_order()

class purchase_order_line(osv.osv, ir_edi.edi):
    _inherit='purchase.order.line'

purchase_order_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
