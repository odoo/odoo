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

from osv import osv
from tools.translate import _

class crm_phonecall2meeting(osv.osv_memory):
    """ Phonecall to Meeting """

    _name = 'crm.phonecall2meeting'
    _description = 'Phonecall To Meeting'

    def action_cancel(self, cr, uid, ids, context=None):
        """
        Closes Phonecall to Meeting form
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Phonecall to Meeting IDs
        @param context: A standard dictionary for contextual values

        """
        return {'type':'ir.actions.act_window_close'}

    def action_make_meeting(self, cr, uid, ids, context=None):
        """ This opens Meeting's calendar view to schedule meeting on current Phonecall
            @return : Dictionary value for created Meeting view
        """
        res = {}
        phonecall_id = context and context.get('active_id', False) or False
        if phonecall_id:
            phonecall = self.pool.get('crm.phonecall').browse(cr, uid, phonecall_id, context)
            res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'base_calendar', 'action_crm_meeting', context)
            res['context'] = {
                'default_phonecall_id': phonecall.id,
                'default_partner_id': phonecall.partner_id and phonecall.partner_id.id or False,
                'default_user_id': uid,
                'default_email_from': phonecall.email_from,
                'default_state': 'open',
                'default_name': phonecall.name,
            }
        return res

crm_phonecall2meeting()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
