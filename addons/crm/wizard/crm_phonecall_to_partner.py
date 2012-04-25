# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
from tools.translate import _

class crm_phonecall2partner(osv.osv_memory):
    """ Converts phonecall to partner """

    _name = 'crm.phonecall2partner'
    _inherit = 'crm.lead2partner'
    _description = 'Phonecall to Partner'
    
    def _select_partner(self, cr, uid, context=None):
        """
        This function Searches for Partner from selected phonecall.
        """
        if context is None:
            context = {}

        phonecall_obj = self.pool.get('crm.phonecall')
        partner_obj = self.pool.get('res.partner')
        contact_obj = self.pool.get('res.partner.address')
        rec_ids = context and context.get('active_ids', [])
        value = {}

        for phonecall in phonecall_obj.browse(cr, uid, rec_ids, context=context):
            partner_ids = partner_obj.search(cr, uid, [('name', '=', phonecall.name or phonecall.name)])
            if not partner_ids and phonecall.email_from:
                address_ids = contact_obj.search(cr, uid, ['|', ('phone', '=', phonecall.partner_phone), ('mobile','=',phonecall.partner_mobile)])
                if address_ids:
                    addresses = contact_obj.browse(cr, uid, address_ids)
                    partner_ids = addresses and [addresses[0].partner_id.id] or False

            partner_id = partner_ids and partner_ids[0] or False
        return partner_id


    def _create_partner(self, cr, uid, ids, context=None):
        """
        This function Creates partner based on action.
        """
        if context is None:
            context = {}
        phonecall = self.pool.get('crm.phonecall')
        data = self.browse(cr, uid, ids, context=context)[0]
        call_ids = context and context.get('active_ids') or []
        partner_id = data.partner_id and data.partner_id.id or False
        return phonecall.convert_partner(cr, uid, call_ids, data.action, partner_id, context=context)

crm_phonecall2partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
