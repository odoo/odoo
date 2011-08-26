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
from datetime import date
class sale_order(osv.osv, ir_edi.edi):
    _inherit = 'sale.order'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Exports a Sale order"""
        edi_struct = {
                'name': True,
                'shop_id': True,
                'origin': True,
                'amount_total': True,
                'date_order': True,
                'create_date': True,
                'date_confirm': True,
                'partner_id': True,
                'partner_invoice_id': True,
                'partner_order_id': True,
                'partner_shipping_id': True,
                'incoterm': True,
                'picking_policy': True,
                'order_policy': True,
                'pricelist_id': True,
                'project_id': True,
                'invoice_quantity': True,
                'order_line': {
                        'name': True,
                        'sequence': True,
                        'product_id': True,
                        'invoiced': True,
                        'procurement_id': True,
                        'price_unit': True,
                        'type': True,
                        'price_subtotal': True,
                        'tax_id': True,
                        'address_allotment_id': True,
                        'product_uom': True,
                        'product_uom_qty': True,
                        'product_uos': True,
                        'notes': True,
                        
                },
                'shipped': True,
        }
        partner_pool = self.pool.get('res.partner')
        partner_address_pool = self.pool.get('res.partner.address')
        company_address_dict = {
            'street': True,
            'street2': True,
            'zip': True,
            'city': True,
            'state_id': True,
            'country_id': True,
            'email': True,
            'phone': True,
                   
        }
        edi_doc_list = []
        for order in records:
            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(sale_order,self).edi_export(cr, uid, [order], edi_struct, context)
            if not edi_doc:
                continue
            edi_doc = edi_doc[0]

            # Add company info and address
            res = partner_pool.address_get(cr, uid, [order.shop_id.company_id.partner_id.id], ['contact', 'order'])
            contact_addr_id = res['contact']
            invoice_addr_id = res['order']

            address = partner_address_pool.browse(cr, uid, invoice_addr_id, context=context)
            edi_company_address_dict = {}
            for key, value in company_address_dict.items():
                if not value:
                   continue
                address_rec = getattr(address, key)
                if not address_rec:
                    continue
                if key.endswith('_id'):
                    address_rec = self.edi_m2o(cr, uid, address_rec, context=context)
                   
                edi_company_address_dict[key] = address_rec
                    
            edi_doc.update({
                    'company_address': edi_company_address_dict,
                    #'company_logo': inv_comp.logo,#TODO
                    #'paid': inv_comp.paid, #TODO
            })
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def edi_import(self, cr, uid, edi_document, context=None):
            
        partner_pool = self.pool.get('res.partner')
        partner_address_pool = self.pool.get('res.partner.address')
        model_data_pool = self.pool.get('ir.model.data')
        product_pool = self.pool.get('product.product')
        product_categ_pool = self.pool.get('product.category')
        company_pool = self.pool.get('res.company')
        country_pool = self.pool.get('res.country')
        state_pool = self.pool.get('res.country.state')
       
        tax_id = []
        account_id = []
        partner_id = None
        company_id = None
        if context is None:
            context = {}
        
        # import company as a new partner, if type==in then supplier=1, else customer=1
        # partner_id field is modified to point to the new partner
        # company_address data used to add address to new partner
        edi_company_address = edi_document['company_address']
        edi_partner_id = edi_document['partner_id']
        company_name = edi_document['company_id'][1]
        state_id = edi_company_address.get('state_id', False)
        state_name = state_id and state_id[1]
        country_id = edi_company_address.get('country_id', False)
        country_name = country_id and country_id[1]

        country_id = country_name and self.edi_import_relation(cr, uid, 'res.country', country_name, context=context) or False
        state_id = state_name and self.edi_import_relation(cr, uid, 'res.country.state', state_name, 
                                values={'country_id': country_id, 'code': state_name}, context=context) or False
        address_value = {
            'street': edi_company_address.get('street', False),
            'street2': edi_company_address.get('street2', False),
            'zip': edi_company_address.get('zip', False),
            'city': edi_company_address.get('city', False),
            'state_id': state_id,
            'country_id': country_id,
            'email': edi_company_address.get('email', False),
            'phone': edi_company_address.get('phone', False),
               
        }
        
        partner_value = {'name': company_name}
        partner_value.update({'customer': True, 'supplier': False})

        partner_id = partner_pool.create(cr, uid, partner_value, context=context)
        address_value.update({'partner_id': partner_id})
        address_id = partner_address_pool.create(cr, uid, address_value, context=context)
        partner_address = partner_address_pool.browse(cr, uid, [address_id], context=context)
        partner_address_id = self.edi_o2m(cr, uid, partner_address, context=context)
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        edi_document['partner_id'] = self.edi_m2o(cr, uid, partner, context=context)
        edi_document.update({
                'partner_invoice_id': partner_address_id,
                'partner_order_id': partner_address_id,
                'partner_shipping_id': partner_address_id,
                #'product_uom_qty': edi_document['order_line'][0]['product_qty'],
                'delay': 10,
        })
        # all fields are converted for sale order import so unnecessary fields are deleted
        del edi_document['order_line'][0]['date_planned']
        del edi_document['order_line'][0]['product_qty']
        del edi_document['date_approve']
        del edi_document['validator']
        
        del edi_document['location_id']
        del edi_document['partner_address_id']
        del edi_document['company_address']
        del edi_document['company_id'] 
        del edi_document['warehouse_id']
        return super(sale_order,self).edi_import(cr, uid, edi_document, context=context)
      
sale_order()

class sale_order_line(osv.osv, ir_edi.edi):
    _inherit='sale.order.line'

sale_order_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
