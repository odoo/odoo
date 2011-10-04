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
from base.ir import ir_edi

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


class res_partner(osv.osv, ir_edi.edi):
    _inherit = "res.partner"

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        return super(res_partner,self).edi_export(cr, uid, records,
                                                  dict(RES_PARTNER_EDI_STRUCT),
                                                  context=context)

class res_partner_address(osv.osv, ir_edi.edi):
    _inherit = "res.partner.address"

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        return super(res_partner_address,self).edi_export(cr, uid, records,
                                                          dict(RES_PARTNER_ADDRESS_EDI_STRUCT),
                                                          context=context)

class res_partner_bank(osv.osv, ir_edi.edi):
    _inherit = "res.partner.bank"

