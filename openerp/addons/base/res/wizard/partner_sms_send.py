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

import wizard
import netsvc
import tools
from osv import fields, osv

class partner_sms_send(osv.osv_memory):
    """ Create Menu """

    _name = "partner.sms.send"
    _description = "Send SMS"

    _columns = {
        'mobile_to': fields.char('To', size=256, required=True),
        'app_id': fields.char('API ID', size=256,required=True),
        'user': fields.char('Login', size=256,required=True),
        'password': fields.char('Password', size=256,required=True),
        'text': fields.text('SMS Message',required=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        @return : default values of fields.
        """
        partner_pool = self.pool.get('res.partner')
        active_ids = context and context.get('active_ids', [])
        res = {}
        for partner in partner_pool.browse(cr, uid, active_ids, context=context):            
            if 'mobile_to' in fields:
                res.update({'mobile_to': partner.mobile})            
        return res

    def sms_send(self, cr, uid, ids, context):
        """
            to send sms

            @param cr: the current row, from the database cursor.
            @param uid: the current user’s ID for security checks.
            @param ids: the ID or list of IDs
            @param context: A standard dictionary
            @return: number indicating the acknowledgement
        """             
        nbr = 0
        
        for data in self.browse(cr, uid, ids, context) :
            tools.sms_send(
                    data.user,
                    data.password, 
                    data.app_id, 
                    tools.ustr(data.text), 
                    data.mobile_to)
            nbr += 1
        return {}
partner_sms_send()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

