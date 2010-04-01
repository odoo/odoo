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

import time
import re
import os

import mx.DateTime
import base64

from tools.translate import _

import tools
from osv import fields,osv,orm
from osv.orm import except_orm

class crm_cases(osv.osv):
    """ crm cases """

    _name = "crm.case"
    _inherit = "crm.case"    

    def msg_new(self, cr, uid, msg):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks
        """

        mailgate_obj = self.pool.get('mail.gateway')
        msg_body = mailgate_obj.msg_body_get(msg)
        msg_subject = mailgate_obj._decode_header(msg['Subject'])
        msg_from = mailgate_obj._decode_header(msg['From'])
        msg_cc = mailgate_obj._decode_header(msg['Cc'])
        body = self.format_body(msg_body['body'])
        data = {   
            'name': msg_subject,         
            'email_from': msg_from,
            'email_cc': msg_cc,            
            'user_id': False,
            'description': body,            
        }
        res = mailgate_obj.partner_get(cr, uid, msg_from)
        if res:
            data.update(res)
        res = self.create(cr, uid, data)        
        cases = self.browse(cr, uid, [res])       
        self._history(cr, uid, cases, _('Receive'), history=True, details=body, email_from=msg_from)
        return res

    def msg_update(self, cr, uid, ids, msg, data={}, default_act='pending'):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of update mail’s IDs """

        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        mailgate_obj = self.pool.get('mail.gateway')
        msg_actions, body_data = mailgate_obj.msg_act_get(msg)
        data.update({
            'description': body_data,
        })
        act = 'case_'+default_act
        if 'state' in msg_actions:
            if msg_actions['state'] in ['draft','close','cancel','open','pending']:
                act = 'case_' + msg_actions['state']

        for k1,k2 in [('cost','planned_cost'),('revenue','planned_revenue'),('probability','probability')]:
            if k1 in msg_actions:
                data[k2] = float(msg_actions[k1])

        if 'priority' in msg_actions:
            if msg_actions['priority'] in ('1','2','3','4','5'):
                data['priority'] = msg_actions['priority']

        if 'partner' in msg_actions:
            data['email_from'] = msg_actions['partner'][:128]        
        msg_from = self._decode_header(msg['From'])
        res = self.write(cr, uid, select, data)
        cases = self.browse(cr, uid, select)       
        self._history(cr, uid, cases, _('Receive'), history=True, details=body_data, email_from=msg['From'])        
        getattr(self,act)(cr, uid, select)
        return res

    def emails_get(self, cr, uid, ids, context={}):

        """ Get Emails
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of email’s IDs
            @param context: A standard dictionary for contextual values

        """
        res = []
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        for case in self.browse(cr, uid, select):
            user_email = (case.user_id and case.user_id.address_id and case.user_id.address_id.email) or False
            res += [(user_email, case.email_from, case.email_cc, getattr(case,'priority') and case.priority or False)]
        if isinstance(ids, (str, int, long)):
            return len(res) and res[0] or False
        return res

    def msg_send(self, cr, uid, id, *args, **argv):

        """ Send The Message
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of email’s IDs
            @param *args: Return Tuple Value
            @param **args: Return Dictionary of Keyword Value
        """
        return True

crm_cases()
