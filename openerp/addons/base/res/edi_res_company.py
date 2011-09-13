# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Tiny SPRL (<http://tiny.be>).
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

from osv import osv
from osv import fields
from tools.translate import _

class res_company(osv.osv):
    _inherit = "res.company"

    def edi_import_as_partner(self, cr, uid, edi_document, values=None, context=None):
        """
        import company as a new partner
        company_address data used to add address to new partner

        edi_document is a dict to have company datas
        edi_document = {
            'company_address': {
                'street': True,
                'street2': True,
                'zip': True,
                'city': True,
                'state_id': True,
                'country_id': True,
                'email': True,
                'phone': True,
                       
            },
            'company_id': True,
        }
        values is a dict to have other datas of partner which are need to import of partner record
        values = {
            'customer': True,
            'supplier': True,
        }
        """
        if values is None:
            values = {}
        partner_pool = self.pool.get('res.partner')
        edi_document_partner = {
            '__model': 'res.partner',
            '__id' : edi_document['company_id'][0],
            'name' : edi_document['company_id'][1],
            'address': [edi_document['company_address']]
        }
        edi_document_partner.update(values)
        return partner_pool.edi_import(cr, uid, edi_document_partner, context=context)

    def edi_export_address(self, cr, uid, records, edi_address_struct=None, context=None):
        if context is None:
            context = {}
        partner_pool = self.pool.get('res.partner')
        partner_address_pool = self.pool.get('res.partner.address')
        if edi_address_struct is None:
            edi_address_struct = {
                'street': True,
                'street2': True,
                'zip': True,
                'city': True,
                'state_id': True,
                'country_id': True,
                'email': True,
                'phone': True,
                       
            }
        edi_company_dict = {}
        for company in records:
            edi_doc = {}
            company_address = False
            res = partner_pool.address_get(cr, uid, [company.partner_id.id], ['contact', 'invoice'])
            addr_id = res['invoice'] or res['contact']
            if addr_id:
                address = partner_address_pool.browse(cr, uid, addr_id, context=context)
                ctx = context.copy()
                ctx.update({'o2m_export':True})
                edi_address_dict_list = partner_address_pool.edi_export(cr, uid, [address], edi_struct=edi_address_struct, context=ctx)
                if edi_address_dict_list:
                    company_address = edi_address_dict_list[0]
            edi_doc.update({
                'company_address': company_address,
                #'company_logo': company.logo,#TODO
            })
            edi_company_dict[company.id] = edi_doc
        return edi_company_dict
res_company()
