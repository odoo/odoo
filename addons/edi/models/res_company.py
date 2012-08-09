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

class res_company(osv.osv):
    """Helper subclass for res.company providing util methods for working with
       companies in the context of EDI import/export. The res.company object
       itself is not EDI-exportable"""
    _inherit = "res.company"

    def edi_export_address(self, cr, uid, company, edi_address_struct=None, context=None):
        """Returns a dict representation of the address of the company record, suitable for
           inclusion in an EDI document, and matching the given edi_address_struct if provided.
           The first found address is returned, in order of preference: invoice, contact, default.

           :param browse_record company: company to export
           :return: dict containing the address representation for the company record, or
                    an empty dict if no address can be found
        """
        res_partner = self.pool.get('res.partner')
        addresses = res_partner.address_get(cr, uid, [company.partner_id.id], ['default', 'contact', 'invoice'])
        addr_id = addresses['invoice'] or addresses['contact'] or addresses['default']
        result = {}
        if addr_id:
            address = res_partner.browse(cr, uid, addr_id, context=context)
            result = res_partner.edi_export(cr, uid, [address], edi_struct=edi_address_struct, context=context)[0]
        if company.logo:
            result['logo'] = company.logo # already base64-encoded
        if company.paypal_account:
            result['paypal_account'] = company.paypal_account
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
