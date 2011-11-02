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
import logging

from osv import fields,osv 
from edi import EDIMixin
from openerp import SUPERUSER_ID
from tools.translate import _

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

    def _get_bank_type(self, cr, uid, context=None):
        # first option: the "normal" bank type, installed by default
        res_partner_bank_type = self.pool.get('res.partner.bank.type')
        try:
            return self.pool.get('ir.model.data').get_object(cr, uid, 'base', 'bank_normal', context=context).code
        except ValueError:
            pass

        # second option: create a new custom type for EDI or use it if already created, as IBAN type is
        # not always appropriate: we need a free-form bank type for max flexibility (users can correct
        # data manually after import)
        code, label = 'edi_generic', 'Generic Bank Type (auto-created for EDI)'
        bank_code_ids = res_partner_bank_type.search(cr, uid, [('code','=',code)], context=context)
        if not bank_code_ids:
            logging.getLogger('edi.res_partner').info('Normal bank account type is missing, creating '
                                                      'a generic bank account type for EDI.')
            self.res_partner_bank_type.create(cr, SUPERUSER_ID, {'name': label,
                                                                 'code': label})
        return code

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
            import_ctx = dict(context,
                              default_partner_id=partner.id,
                              default_state=self._get_bank_type(cr, uid, context))
            for ext_bank_id, bank_name in edi_bank_ids:
                try:
                    self.edi_import_relation(cr, uid, 'res.partner.bank',
                                             bank_name, ext_bank_id, context=import_ctx)
                except osv.except_osv:
                    # failed to import it, try again with unrestricted default type
                    logging.getLogger('edi.res_partner').warning('Failed to import bank account using'
                                                                 'bank type: %s, ignoring', import_ctx['default_state'],
                                                                 exc_info=True)
        return result