# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011-2012 OpenERP S.A. <http://openerp.com>
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

from openerp.osv import osv
from openerp.tools.translate import _
from openerp.addons.edi import EDIMixin

PURCHASE_ORDER_LINE_EDI_STRUCT = {
    'name': True,
    'date_planned': True,
    'product_id': True,
    'product_uom': True,
    'price_unit': True,
    'product_qty': True,

    # fields used for web preview only - discarded on import
    'price_subtotal': True,
}

PURCHASE_ORDER_EDI_STRUCT = {
    'company_id': True, # -> to be changed into partner
    'name': True,
    'partner_ref': True,
    'origin': True,
    'date_order': True,
    'partner_id': True,
    #custom: 'partner_address',
    'notes': True,
    'order_line': PURCHASE_ORDER_LINE_EDI_STRUCT,
    #custom: currency_id

    # fields used for web preview only - discarded on import
    'amount_total': True,
    'amount_untaxed': True,
    'amount_tax': True,
    'state':True,
}

class purchase_order(osv.osv, EDIMixin):
    _inherit = 'purchase.order'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Exports a purchase order"""
        edi_struct = dict(edi_struct or PURCHASE_ORDER_EDI_STRUCT)
        res_company = self.pool.get('res.company')
        res_partner_obj = self.pool.get('res.partner')
        edi_doc_list = []
        for order in records:
            # generate the main report
            self._edi_generate_report_attachment(cr, uid, order, context=context)

            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(purchase_order,self).edi_export(cr, uid, [order], edi_struct, context)[0]
            edi_doc.update({
                    # force trans-typing to purchase.order upon import
                    '__import_model': 'sale.order',
                    '__import_module': 'sale',

                    'company_address': res_company.edi_export_address(cr, uid, order.company_id, context=context),
                    'partner_address': res_partner_obj.edi_export(cr, uid, [order.partner_id], context=context)[0],
                    'currency': self.pool.get('res.currency').edi_export(cr, uid, [order.pricelist_id.currency_id],
                                                                         context=context)[0],
            })
            if edi_doc.get('order_line'):
                for line in edi_doc['order_line']:
                    line['__import_model'] = 'sale.order.line'
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def edi_import_company(self, cr, uid, edi_document, context=None):
        # TODO: for multi-company setups, we currently import the document in the
        #       user's current company, but we should perhaps foresee a way to select
        #       the desired company among the user's allowed companies

        self._edi_requires_attributes(('company_id','company_address'), edi_document)
        res_partner = self.pool.get('res.partner')

        xid, company_name = edi_document.pop('company_id')
        # Retrofit address info into a unified partner info (changed in v7 - used to keep them separate)
        company_address_edi = edi_document.pop('company_address')
        company_address_edi['name'] = company_name
        company_address_edi['is_company'] = True
        company_address_edi['__import_model'] = 'res.partner'
        company_address_edi['__id'] = xid  # override address ID, as of v7 they should be the same anyway
        if company_address_edi.get('logo'):
            company_address_edi['image'] = company_address_edi.pop('logo')
        company_address_edi['supplier'] = True
        partner_id = res_partner.edi_import(cr, uid, company_address_edi, context=context)

        # modify edi_document to refer to new partner
        partner = res_partner.browse(cr, uid, partner_id, context=context)
        partner_edi_m2o = self.edi_m2o(cr, uid, partner, context=context)
        edi_document['partner_id'] = partner_edi_m2o
        edi_document.pop('partner_address', None) # ignored, that's supposed to be our own address!
        return partner_id

    def _edi_get_pricelist(self, cr, uid, partner_id, currency, context=None):
        # TODO: refactor into common place for purchase/sale, e.g. into product module
        partner_model = self.pool.get('res.partner')
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        pricelist = partner.property_product_pricelist_purchase
        if not pricelist:
            pricelist = self.pool.get('ir.model.data').get_object(cr, uid, 'purchase', 'list0', context=context)

        if not pricelist.currency_id == currency:
            # look for a pricelist with the right type and currency, or make a new one
            pricelist_type = 'purchase'
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

    def _edi_get_location(self, cr, uid, partner_id, context=None):
        partner_model = self.pool.get('res.partner')
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        location = partner.property_stock_customer
        if not location:
            location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_stock', context=context)
        return self.edi_m2o(cr, uid, location, context=context)

    def edi_import(self, cr, uid, edi_document, context=None):
        self._edi_requires_attributes(('company_id','company_address','order_line','date_order','currency'), edi_document)

        #import company as a new partner
        partner_id = self.edi_import_company(cr, uid, edi_document, context=context)

        # currency for rounding the discount calculations and for the pricelist
        res_currency = self.pool.get('res.currency')
        currency_info = edi_document.pop('currency')
        currency_id = res_currency.edi_import(cr, uid, currency_info, context=context)
        order_currency = res_currency.browse(cr, uid, currency_id)

        partner_ref = edi_document.pop('partner_ref', False)
        edi_document['partner_ref'] = edi_document['name']
        edi_document['name'] = partner_ref or edi_document['name']
        edi_document['pricelist_id'] = self._edi_get_pricelist(cr, uid, partner_id, order_currency, context=context)
        edi_document['location_id'] = self._edi_get_location(cr, uid, partner_id, context=context)

        # discard web preview fields, if present
        edi_document.pop('amount_total', None)
        edi_document.pop('amount_tax', None)
        edi_document.pop('amount_untaxed', None)
        edi_document.pop('payment_term', None)
        edi_document.pop('order_policy', None)
        edi_document.pop('user_id', None)

        for order_line in edi_document['order_line']:
            self._edi_requires_attributes(('date_planned', 'product_id', 'product_uom', 'product_qty', 'price_unit'), order_line)
            # original sale order contains unit price and discount, but not final line price
            discount = order_line.pop('discount', 0.0)
            if discount:
                order_line['price_unit'] = res_currency.round(cr, uid, order_currency,
                                                              (order_line['price_unit'] * (1 - (discount or 0.0) / 100.0)))
            # sale order lines have sequence numbers, not purchase order lines
            order_line.pop('sequence', None)

            # discard web preview fields, if present
            order_line.pop('price_subtotal', None)
        return super(purchase_order,self).edi_import(cr, uid, edi_document, context=context)

class purchase_order_line(osv.osv, EDIMixin):
    _inherit='purchase.order.line'

