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
from datetime import date, datetime

class sale_order(osv.osv, ir_edi.edi):
    _inherit = 'sale.order'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Exports a Sale order"""
        edi_struct = {
            'company_id': True, # -> to be changed into partner
            'name': True,
            'client_order_ref': True,
            'origin': True,
            'date_order': True,
            'partner_id': True,
            'partner_order_id': True, #only one address needed
                    #SO: 'partner_order_id'
                    #PO: 'partner_address_id'
            'pricelist_id': True,
            'note': True,
                    #SO: 'note'
                    #PO: 'notes'
            'amount_total': True,
            'amount_tax': True,
            'amount_untaxed': True,
            'order_line': {
                'sequence': True,
                        #SO: yes
                        #PO: No
                'name': True,
                'delay': True,
                        #SO: 'delay' : 'date_order' - 'date_planned'
                        #PO: 'date_planned': 'date_order' + 'delay'

                'product_id': True,
                'product_uom': True,
                'price_unit': True,
                'product_uom_qty': True,
                        #SO: 'product_uom_qty'
                        #PO: 'product_qty'
                'price_subtotal': True,
                'discount': True,
                        #SO: yes
                        #PO: No
                'notes': True,
            }
        }
        res_company = self.pool.get('res.company')
        edi_doc_list = []
        for order in records:
            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(sale_order,self).edi_export(cr, uid, [order], edi_struct, context)[0]
            currency = order.company_id.currency_id
            edi_address = res_company.edi_export_address(cr, uid, [order.company_id], context=context)[0]
            edi_doc.update(company_address=edi_address,
                           currency_id=(currency and self.edi_m2o(cr, uid, currency, context=context) or False))
            #TODO: company_logo
            edi_doc_list.append(edi_doc)
        return edi_doc_list


    def edi_import_company(self, cr, uid, edi_document, context=None):
        partner_address_pool = self.pool.get('res.partner.address')
        partner_pool = self.pool.get('res.partner')
        company_pool = self.pool.get('res.company')

        # import company as a new partner, supplier=1.
        # company_address data used to add address to new partner
        partner_value = {'supplier': True}
        partner_id = company_pool.edi_import_as_partner(cr, uid, edi_document, values=partner_value, context=context)


        # partner_id field is modified to point to the new partner
        res = partner_pool.address_get(cr, uid, [partner_id], ['contact', 'invoice'])
        address_id = res['invoice']
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        partner_address = partner_address_pool.browse(cr, uid, address_id, context=context)
        edi_document['partner_id'] = self.edi_m2o(cr, uid, partner, context=context)
        edi_document['partner_order_id'] = self.edi_m2o(cr, uid, partner_address, context=context)
        edi_document['partner_invoice_id'] = edi_document['partner_order_id']
        edi_document['partner_shipping_id'] = edi_document['partner_order_id']
        del edi_document['company_id']
        return partner_id

    def edi_get_pricelist(self, cr, uid, partner_id, context=None):
        # value = ["724f93ec-ddd0-11e0-88ec-701a04e25543:product.list0", "Public Pricelist (EUR)"]
        partner_model = self.pool.get('res.partner')
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        pricelist = partner.property_product_pricelist
        if not pricelist:
            pricelist = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'list0', context=context)
        return self.edi_m2o(cr, uid, pricelist, context=context)

    def edi_import(self, cr, uid, edi_document, context=None):
        if context is None:
            context = {}

        #import company as a new partner
        partner_id = self.edi_import_company(cr, uid, edi_document, context=context)

        date_order = edi_document.get('date_order', False)
        edi_document['client_order_ref'] = edi_document['name']
        edi_document['note'] = edi_document.get('notes', False)
        edi_document['pricelist_id'] = self.edi_get_pricelist(cr, uid, partner_id, context=context)
        order_lines = edi_document['order_line']
        for order_line in order_lines:
            order_line['product_uom_qty'] = order_line['product_qty']
            date_planned = order_line['date_planned']
            delay = 0
            if date_order and date_planned:
                delay = (datetime.strptime(date_planned, "%Y-%m-%d") - datetime.strptime(date_order, "%Y-%m-%d")).days
            order_line['delay'] = delay
        return super(sale_order,self).edi_import(cr, uid, edi_document, context=context)
      
sale_order()

class sale_order_line(osv.osv, ir_edi.edi):
    _inherit='sale.order.line'

sale_order_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
