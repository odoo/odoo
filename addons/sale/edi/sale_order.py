# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>
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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from osv import fields, osv, orm
from edi import EDIMixin
from tools import DEFAULT_SERVER_DATE_FORMAT

SALE_ORDER_LINE_EDI_STRUCT = {
    'sequence': True,
            #SO: yes
            #PO: No
    'name': True,
    #custom: 'planned_date'
    'product_id': True,
    'product_uom': True,
    'price_unit': True,
    #custom: 'product_qty'
    'discount': True,
            #SO: yes
            #PO: No
    'notes': True,
}

SALE_ORDER_EDI_STRUCT = {
    'name': True,
    'origin': True,
    'company_id': True, # -> to be changed into partner
    #custom: 'partner_ref'
    'date_order': True,
    'partner_id': True,
    #custom: 'partner_address'
    #custom: 'notes'
    'order_line': SALE_ORDER_LINE_EDI_STRUCT
}

class sale_order(osv.osv, EDIMixin):
    _inherit = 'sale.order'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Exports a Sale order"""
        edi_struct = dict(edi_struct or SALE_ORDER_EDI_STRUCT)
        res_company = self.pool.get('res.company')
        res_partner_address = self.pool.get('res.partner.address')
        edi_doc_list = []
        for order in records:
            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(sale_order,self).edi_export(cr, uid, [order], edi_struct, context)[0]
            edi_doc.update({
                    # force trans-typing to purchase.order upon import
                    '__import_model': 'purchase',
                    '__import_module': 'purchase',

                    'company_address': res_company.edi_export_address(cr, uid, order.company_id, context=context),
                    'company_paypal_account': order.company_id.paypal_account,
                    'partner_address': res_partner_address.edi_export(cr, uid, [order.partner_order_id], context=context)[0],

                    'currency_id': self.edi_m2o(cr, uid, order.company_id.currency_id, context=context),
                    'partner_ref': order.client_order_ref or False,
                    'notes': order.note or False,
                    #TODO: company_logo
            })
            edi_doc_list.append(edi_doc)
        return edi_doc_list


    def _edi_import_company(self, cr, uid, edi_document, context=None):
        # TODO: for multi-company setups, we currently import the document in the
        #       user's current company, but we should perhaps foresee a way to select
        #       the desired company among the user's allowed companies

        self._edi_requires_attributes(('company_id','company_address'), edi_document)
        res_partner_address = self.pool.get('res.partner.address')
        res_partner = self.pool.get('res.partner')

        # imported company = as a new partner
        src_company_id, src_company_name = edi_document.pop('company_id')
        partner_id = self.edi_import_relation(cr, uid, 'res.partner', src_company_name,
                                              src_company_id, context=context)
        partner_value = {'supplier': True}
        res_partner.write(cr, uid, [partner_id], partner_value, context=context)

        # imported company_address = new partner address
        address_info = edi_document.pop('company_address')
        address_info['partner_id'] = (src_company_id, src_company_name)
        address_info['type'] = 'default'
        address_id = res_partner_address.edi_import(cr, uid, address_info, context=context)

        # modify edi_document to refer to new partner/address
        partner_address = res_partner_address.browse(cr, uid, address_id, context=context)
        edi_document['partner_id'] = (src_company_id, src_company_name)
        edi_document.pop('partner_address', False) # ignored
        address_edi_m2o = self.edi_m2o(cr, uid, partner_address, context=context)
        edi_document['partner_order_id'] = address_edi_m2o
        edi_document['partner_invoice_id'] = address_edi_m2o
        edi_document['partner_shipping_id'] = address_edi_m2o

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
        self._edi_requires_attributes(('company_id','company_address','order_line','date_order'), edi_document)

        #import company as a new partner
        partner_id = self._edi_import_company(cr, uid, edi_document, context=context)

        date_order = edi_document['date_order']
        edi_document['client_order_ref'] = edi_document.pop('partner_ref', False)
        edi_document['note'] = edi_document.pop('notes', False)
        edi_document['pricelist_id'] = self.edi_get_pricelist(cr, uid, partner_id, context=context)
        order_lines = edi_document['order_line']
        for order_line in order_lines:
            order_line['product_uom_qty'] = order_line['product_qty']
            del order_line['product_qty']
            date_planned = order_line.pop('date_planned')
            delay = 0
            if date_order and date_planned:
                # no security_days buffer, this is the promised date given by supplier
                delay = (datetime.strptime(date_planned, DEFAULT_SERVER_DATE_FORMAT) - \
                         datetime.strptime(date_order, DEFAULT_SERVER_DATE_FORMAT)).days
            order_line['delay'] = delay
        return super(sale_order,self).edi_import(cr, uid, edi_document, context=context)

class sale_order_line(osv.osv, EDIMixin):
    _inherit='sale.order.line'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        edi_struct = dict(edi_struct or SALE_ORDER_LINE_EDI_STRUCT)
        edi_doc_list = []
        for line in records:
            edi_doc = super(sale_order_line,self).edi_export(cr, uid, [line], edi_struct, context)[0]
            edi_doc['product_qty'] = line.product_uom_qty
            if line.product_uos:
                edi_doc.update(product_uom=line.product_uos,
                               product_qty=line.product_uos_qty)

            # company.security_days is for internal use, so customer should only
            # see the expected date_planned based on line.delay 
            date_planned = datetime.strptime(line.order_id.date_order, DEFAULT_SERVER_DATE_FORMAT) + \
                            relativedelta(days=line.delay or 0.0)
            edi_doc['date_planned'] = date_planned.strftime(DEFAULT_SERVER_DATE_FORMAT)
            edi_doc_list.append(edi_doc)
        return edi_doc_list

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: