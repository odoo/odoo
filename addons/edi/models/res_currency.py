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

from osv import fields,osv 
from edi import EDIMixin
from openerp import SUPERUSER_ID

RES_CURRENCY_EDI_STRUCT = {
    #custom: 'code'
    'symbol': True,
    'rate': True,
}

class res_currency(osv.osv, EDIMixin):
    _inherit = "res.currency"

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        edi_struct = dict(edi_struct or RES_CURRENCY_EDI_STRUCT)
        edi_doc_list = []
        for currency in records:
            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(res_currency,self).edi_export(cr, uid, [currency], edi_struct, context)[0]
            edi_doc.update(code=currency.name)
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def edi_import(self, cr, uid, edi_document, context=None):
        self._edi_requires_attributes(('code','symbol'), edi_document)
        external_id = edi_document['__id']
        existing_currency = self._edi_get_object_by_external_id(cr, uid, external_id, 'res_currency', context=context)
        if existing_currency:
            return existing_currency.id

        # find with unique ISO code
        existing_ids = self.search(cr, uid, [('name','=',edi_document['code'])])
        if existing_ids:
            return existing_ids[0]

        # nothing found, create a new one
        currency_id = self.create(cr, SUPERUSER_ID, {'name': edi_document['code'],
                                                     'symbol': edi_document['symbol']}, context=context)
        rate = edi_document.pop('rate')
        if rate:
            self.pool.get('res.currency.rate').create(cr, SUPERUSER_ID, {'currency_id': currency_id,
                                                                         'rate': rate}, context=context)
        return currency_id




#class res_currency(osv.osv):
#    """Helper subclass for res.currency providing util methods for working with
#       currencies in the context of EDI import/export. The res.currency object
#       itself is not EDI-exportable by itself"""
#    _inherit = "res.currency"
#
#
#
#
#    def edi_export_currency(self, cr, uid, edi_record, currency, context=None):
#        """Returns a dict representation of the given currency, suitable for
#           inclusion in an EDI document.
#
#           :param EDIMixin edi_record: record for which the currency is being exported
#           :param browse_record currency: currency record to export
#           :return: dict containing the address representation for the currency record,
#                    similar to a normal EDI Many2One record, with some extra data. 
#        """
#        result = edi_record.edi_m2o(cr, uid, currency_id, context=context)
#        currency = self.pool.get('res.partner').browse(currency_id)
#        result.update(symbol=currency.symbol,
#                      rate=currency.rate)
#        return result
#
#    def edi_import_currency(self, cr, uid, edi_record, currency, context=None):
#        """Retrieve and possibly create a currency EDI specification``[external_id,value]`` for the
#           given model, returning the corresponding database ID:
#
#           :param EDIMixin edi_record: record for which the currency is being exported
#           :param browse_record currency: currency record to export
#           :return: dict containing the address representation for the currency record,
#                    similar to a normal EDI Many2One record, with some extra data. 
#        """
#        result = edi_record.edi_m2o(cr, uid, currency_id, context=context)
#        currency = self.pool.get('res.partner').browse(currency_id)
#        result.update(symbol=currency.symbol,
#                      rate=currency.rate)
#        return result