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

import time
import re
import os

import mx.DateTime
import base64

from tools.translate import _

import tools
from osv import fields,osv,orm
from osv.orm import except_orm
class crm_job(osv.osv):
    _name = "crm.job"
    _description = "Job Cases"
    _order = "id desc"
    _inherits = {'crm.case':"inherit_case_id"}    
    _columns = {        
        'inherit_case_id': fields.many2one('crm.case','Case',ondelete='cascade'),
    }
    def _map_ids(self, method, cr, uid, ids, *args, **argv):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids            
        case_data = self.browse(cr, uid, select)
        new_ids = []
        for case in case_data:
            if case.inherit_case_id:
                new_ids.append(case.inherit_case_id.id)
        res = getattr(self.pool.get('crm.case'),method)(cr, uid, new_ids, *args, **argv)
        if isinstance(ids, (str, int, long)) and isinstance(res, list):
            return res and res[0] or False
        return res


    def onchange_case_id(self, cr, uid, ids, *args, **argv):
        return self._map_ids('onchange_case_id',cr,uid,ids,*args,**argv)
    def stage_next(self, cr, uid, ids, *args, **argv):
        return self._map_ids('stage_next',cr,uid,ids,*args,**argv)
    def onchange_partner_id(self, cr, uid, ids, *args, **argv):
        return self._map_ids('onchange_partner_id',cr,uid,ids,*args,**argv)
    def onchange_partner_address_id(self, cr, uid, ids, *args, **argv):
        return self._map_ids('onchange_partner_address_id',cr,uid,ids,*args,**argv)
    def onchange_categ_id(self, cr, uid, ids, *args, **argv):
        return self._map_ids('onchange_categ_id',cr,uid,ids,*args,**argv)
    def case_close(self,cr, uid, ids, *args, **argv):
        return self._map_ids('case_close',cr,uid,ids,*args,**argv)    
    def case_open(self,cr, uid, ids, *args, **argv):
        return self._map_ids('case_open',cr,uid,ids,*args,**argv)
    def case_cancel(self,cr, uid, ids, *args, **argv):
        return self._map_ids('case_cancel',cr,uid,ids,*args,**argv)
    def case_reset(self,cr, uid, ids, *args, **argv):
        return self._map_ids('case_reset',cr,uid,ids,*args,**argv)   

    def msg_new(self, cr, uid, msg):        
        mailgate_obj = self.pool.get('mail.gateway')
        msg_body = mailgate_obj.msg_body_get(msg)
        data = {
            'name': msg['Subject'],            
            'email_from': msg['From'],
            'email_cc': msg['Cc'],            
            'user_id': False,
            'description': msg_body['body'],
            'history_line': [(0, 0, {'description': msg_body['body'], 'email': msg['From'] })],
        }
        res = mailgate_obj.partner_get(cr, uid, msg['From'])
        if res:
            data.update(res)
        res = self.create(cr, uid, data)        
        return res

    def msg_update(self, cr, uid, ids, *args, **argv):
        return self._map_ids('msg_update',cr, uid, ids, *args, **argv)
    def emails_get(self, cr, uid, ids, *args, **argv):
        return self._map_ids('emails_get',cr, uid, ids, *args, **argv)
    def msg_send(self, cr, uid, ids, *args, **argv):        
        return self._map_ids('msg_send',cr, uid, ids, *args, **argv) 
crm_job()
