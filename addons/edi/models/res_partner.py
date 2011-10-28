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
from osv import fields,osv 
from edi import EDIMixin

RES_PARTNER_ADDRESS_EDI_STRUCT = {
    'name': True,
    'email': True,
    'street': True,
    'street2': True,
    'zip': True,
    'city': True,
    'country_id': True,
    'state_id': True,
    'phone': True,
    'fax': True,
    'mobile': True,
}

RES_PARTNER_EDI_STRUCT = {
    'name': True,
    'ref': True,
    'lang': True,
    'website': True,
    'address': RES_PARTNER_ADDRESS_EDI_STRUCT
}

class res_partner(osv.osv, EDIMixin):
    _inherit = "res.partner"

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        return super(res_partner,self).edi_export(cr, uid, records,
                                                  edi_struct or dict(RES_PARTNER_EDI_STRUCT),
                                                  context=context)

class res_partner_address(osv.osv, EDIMixin):
    _inherit = "res.partner.address"

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        return super(res_partner_address,self).edi_export(cr, uid, records,
                                                          edi_struct or dict(RES_PARTNER_ADDRESS_EDI_STRUCT),
                                                          context=context)

    def edi_import(self, cr, uid, edi_document, context=None):
        # handle bank info, if any
        edi_bank_ids = edi_document.pop('bank_ids', None)
        result = super(res_partner_address,self).edi_import(cr, uid, edi_document, context=context)
        if edi_bank_ids:
            partner = self._edi_get_object_by_external_id(cr, uid, edi_document['partner_id'][0],
                                                          'res.partner', context=context)
            assert partner is not None
            import_ctx = dict(context, default_partner_id=partner.id)
            bank_ids = []
            for ext_bank_id, bank_name in edi_bank_ids:
                bank_ids.append(self.edi_import_relation(cr, uid, 'res.partner.bank',
                                                         bank_name, ext_bank_id, context=import_ctx))
        return 