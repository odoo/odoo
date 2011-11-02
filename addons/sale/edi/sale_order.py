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
    'name': True,
    #custom: 'date_planned'
    'product_id': True,
    'product_uom': True,
    'price_unit': True,
    #custom: 'product_qty'
    'discount': True,
    'notes': True,

    # fields used for web preview only - discarded on import
    'price_subtotal': True,
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
    'order_line': SALE_ORDER_LINE_EDI_STRUCT,

    # fields used for web preview only - discarded on import
    'amount_total': True,
    'amount_untaxed': True,
    'amount_tax': True,
    'payment_term': True,
    'order_policy': True,
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
            # generate the main report
            self._edi_generate_report_attachment(cr, uid, order, context=context)

            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(sale_order,self).edi_export(cr, uid, [order], edi_struct, context)[0]
            edi_doc.update({
                    # force trans-typing to purchase.order upon import
                    '__import_model': 'purchase',
                    '__import_module': 'purchase',

                    'company_address': res_company.edi_export_address(cr, uid, order.company_id, context=context),
                    'company_paypal_account': order.company_id.paypal_account,
                    'partner_address': res_partner_address.edi_export(cr, uid, [order.partner_order_id], context=context)[0],

                    'currency': self.pool.get('res.currency').edi_export(cr, uid, [order.pricelist_id.currency_id],
                                                                         context=context)[0],
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

    def _edi_get_pricelist(self, cr, uid, partner_id, currency, context=None):
        # TODO: refactor into common place for purchase/sale, e.g. into product module
        partner_model = self.pool.get('res.partner')
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        pricelist = partner.property_product_pricelist
        if not pricelist:
            pricelist = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'list0', context=context)

        if not pricelist.currency_id == currency:
            # look for a pricelist with the right type and currency, or make a new one
            pricelist_type = 'sale'
            product_pricelist = self.pool.get('product.pricelist')
            match_pricelist_ids = product_pricelist.search(cr, uid,[('type','=',pricelist_type),
                                                                    ('currency_id','=',currency.id)])
            if match_pricelist_ids:
                pricelist_id = match_pricelist_ids[0]
            else:
                pricelist_name = _('EDI Pricelist (%s)') % (currency.name,)
                pricelist_id = product_pricelist.create(cr, uid, {'name': pricelist_name,
                                                                  'type': pricelist_type,
                                                                  'currency_id': currency.id,
                                                                 })
                self.pool.get('product.pricelist.version').create(cr, uid, {'name': pricelist_name,
                                                                            'pricelist_id': pricelist_id})
            pricelist = product_pricelist.browse(cr, uid, pricelist_id)

        return self.edi_m2o(cr, uid, pricelist, context=context)

    def edi_import(self, cr, uid, edi_document, context=None):
        self._edi_requires_attributes(('company_id','company_address','order_line','date_order','currency'), edi_document)

        #import company as a new partner
        partner_id = self._edi_import_company(cr, uid, edi_document, context=context)

        # currency for rounding the discount calculations and for the pricelist
        res_currency = self.pool.get('res.currency')
        currency_info = edi_document.pop('currency')
        currency_id = res_currency.edi_import(cr, uid, currency_info, context=context)
        order_currency = res_currency.browse(cr, uid, currency_id)

        date_order = edi_document['date_order']
        partner_ref = edi_document.pop('partner_ref', False)
        edi_document['client_order_ref'] = edi_document['name']
        edi_document['name'] = partner_ref or edi_document['name']
        edi_document['note'] = edi_document.pop('notes', False)
        edi_document['pricelist_id'] = self._edi_get_pricelist(cr, uid, partner_id, order_currency, context=context)

        # discard web preview fields, if present
        edi_document.pop('amount_total', None)
        edi_document.pop('amount_tax', None)
        edi_document.pop('amount_untaxed', None)

        order_lines = edi_document['order_line']
        for order_line in order_lines:
            self._edi_requires_attributes(('date_planned', 'product_id', 'product_uom', 'product_qty', 'price_unit'), order_line)
            order_line['product_uom_qty'] = order_line['product_qty']
            del order_line['product_qty']
            date_planned = order_line.pop('date_planned')
            delay = 0
            if date_order and date_planned:
                # no security_days buffer, this is the promised date given by supplier
                delay = (datetime.strptime(date_planned, DEFAULT_SERVER_DATE_FORMAT) - \
                         datetime.strptime(date_order, DEFAULT_SERVER_DATE_FORMAT)).days
            order_line['delay'] = delay

            # discard web preview fields, if present
            order_line.pop('price_subtotal', None)
        return super(sale_order,self).edi_import(cr, uid, edi_document, context=context)

class sale_order_line(osv.osv, EDIMixin):
    _inherit='sale.order.line'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Overridden to provide sale order line fields with the expected names
           (sale and purchase orders have different column names)"""
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