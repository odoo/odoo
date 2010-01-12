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

import tools
from osv import fields, osv
import os
import pooler
import netsvc
from tools.translate import _

class crm_claim(osv.osv):
    _name = "crm.claim"
    _description = "Claim Cases"
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
    def case_escalate(self,cr, uid, ids, *args, **argv):
        return self._map_ids('case_escalate',cr,uid,ids,*args,**argv)
    def case_pending(self,cr, uid, ids, *args, **argv):
        return self._map_ids('case_pending',cr,uid,ids,*args,**argv)

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
crm_claim()


class crm_claim_assign_wizard(osv.osv_memory):
    _name = 'crm.claim.assign_wizard'

    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Section', required=False),
        'user_id': fields.many2one('res.users', 'Responsible'),
    }

    def _get_default_section(self, cr, uid, context):
        case_id = context.get('active_id',False)
        if not case_id:
            return False
        case_obj = self.pool.get('crm.claim')
        case = case_obj.read(cr, uid, case_id, ['state','section_id'])
        if case['state'] in ('done'):
            raise osv.except_osv(_('Error !'), _('You can not assign Closed Case.'))
        return case['section_id']


    _defaults = {
        'section_id': _get_default_section
    }
    def action_create(self, cr, uid, ids, context=None):
        case_obj = self.pool.get('crm.claim')
        case_id = context.get('active_id',[])
        res = self.read(cr, uid, ids)[0]
        case = case_obj.browse(cr, uid, case_id)
        if case.state in ('done'):
            raise osv.except_osv(_('Error !'), _('You can not assign Closed Case.'))
        new_case_id = case_obj.copy(cr, uid, case_id, default=
                                            {
                                                'section_id':res.get('section_id',False),
                                                'user_id':res.get('user_id',False),
                                                'case_id' : case.inherit_case_id.id
                                            }, context=context)
        case_obj.case_close(cr, uid, [case_id])

        data_obj = self.pool.get('ir.model.data')
        result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_claims_filter')
        search_view = data_obj.read(cr, uid, result, ['res_id'])
        value = {
            'name': _('Claims'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'crm.claim',
            'res_id': int(new_case_id),
            'type': 'ir.actions.act_window',
            'search_view_id': search_view['res_id']
        }
        return value

crm_claim_assign_wizard()
