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

#from osv import osv
#from osv import fields
#from tools.translate import _

# TODO: CHECK below, seems useless
#
#class res_company(osv.osv):
#    """Helper subclass for res.company providing util methods for working with
#       companies in the context of EDI import/export. The res.company object
#       itself is not EDI-exportable"""
#   _inherit = "res.company"
#
#    def edi_import_as_partner(self, cr, uid, edi_document, values=None, context=None):
#        """
#        import company as a new partner
#        company_address data used to add address to new partner
#
#        edi_document is a dict to have company datas
#        edi_document = {
#            'company_address': {
#                'street': True,
#                'street2': True,
#                'zip': True,
#                'city': True,
#                'state_id': True,
#                'country_id': True,
#                'email': True,
#                'phone': True,
#                       
#            },
#            'company_id': True,
#        }
#        values is a dict to have other datas of partner which are need to import of partner record
#        values = {
#            'customer': True,
#            'supplier': True,
#        }
#        """
#        if values is None:
#            values = {}
#        partner_model = 'res.partner'
#        partner_pool = self.pool.get(partner_model)
#        xml_id = edi_document['company_id'][0]
#        company_address = edi_document.get('company_address', False)
#        partner_name = edi_document['company_id'][1]
#        partner = partner_pool.edi_get_object(cr, uid, xml_id, partner_model, context=context)
#        if not partner:
#            partner = partner_pool.edi_get_object_by_name(cr, uid, partner_name, partner_model, context=context)
#
#        if partner:
            #FIXME
#            record_xml = partner_pool._get_external_id(cr, uid, [partner.id], context=context)
#            if record_xml:
#                module, xml_id = record_xml
#                xml_id = '%s.%s' % (module, xml_id)
#
#        edi_document_partner = {
#            '__model': partner_model,
#            '__id' : xml_id,
#            'name' : partner_name,
#        }
#        if company_address:
#            edi_document_partner['address'] = [company_address]
#
#        edi_document_partner.update(values)
#        return partner_pool.edi_import(cr, uid, edi_document_partner, context=context)
#
#    def edi_export_address(self, cr, uid, records, edi_address_struct=None, context=None):
#        """Return a dict representation of the address of each company record, suitable for
#           inclusion in an EDI document, and matching the given edi_address_struct if provided.
#
#           :param list(browse_record) records: list of companies to export
#           :rtype: list(dict)
#           :return: list of dicts, where each dict contains the address representation for
#                    the company record as the same index in ``records``.
#        """
#        if context is None:
#            context = {}
#        res_partner = self.pool.get('res.partner')
#        res_partner_address = self.pool.get('res.partner.address')
#        if edi_address_struct is None:
#            edi_address_struct = {
#                'street': True,
#                'street2': True,
#                'zip': True,
#                'city': True,
#                'state_id': True,
#                'country_id': True,
#                'email': True,
#                'phone': True,
#            }
#        results = []
#        for company in records:
#            res = res_partner.address_get(cr, uid, [company.partner_id.id], ['default', 'contact', 'invoice'])
#            addr_id = res['invoice'] or res['contact'] or res['default']
#            result = {}
#            if addr_id:
#                address = res_partner_address.browse(cr, uid, addr_id, context=context)
#                result = res_partner_address.edi_export(cr, uid, [address], edi_struct=edi_address_struct, context=ctx)[0]
#            results.append(result)
#        return results

