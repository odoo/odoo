 #-*- coding: utf-8 -*-
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

class crm_project_bug(osv.osv):
    _name = "crm.project.bug"
    _description = "Project Bug Cases"
    _order = "id desc"
    _inherits = {'crm.case':"inherit_case_id"}    
    _columns = {        
           'inherit_case_id':fields.many2one('crm.case','Case'),
           'project_id':fields.many2one('project.project', 'Project'),
    }
    
    def _map_ids(self, method, cr, uid, ids, *args, **argv):
        case_data = self.browse(cr, uid, ids)
        new_ids = []
        for case in case_data:
            if case.inherit_case_id:
                new_ids.append(case.inherit_case_id.id)
        return getattr(self.pool.get('crm.case'),method)(cr, uid, new_ids, *args, **argv)


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
    


crm_project_bug()

class crm_bug_assign_wizard(osv.osv_memory):
    _name = 'crm.project.bug.assign_wizard'

    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Section', required=True),
        'user_id': fields.many2one('res.users', 'Responsible'),
    }

    def _get_default_section(self, cr, uid, context):
        case_id = context.get('active_id',False)
        if not case_id:
            return False
        case_obj = self.pool.get('crm.project.bug')
        case = case_obj.read(cr, uid, case_id, ['state','section_id'])
        if case['state'] in ('done'):
            raise osv.except_osv(_('Error !'), _('You can not assign Closed Case.'))
        return case['section_id']


    _defaults = {
        'section_id': _get_default_section
    }
    def action_create(self, cr, uid, ids, context=None):
        case_obj = self.pool.get('crm.project.bug')
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
        result = data_obj._get_id(cr, uid, 'crm_project', 'view_crm_case_bugs_filter')
        search_view = data_obj.read(cr, uid, result, ['res_id'])
        value = {            
            'name': _('Bugs'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'crm.project.bug',
            'res_id': int(new_case_id),            
            'type': 'ir.actions.act_window', 
            'search_view_id': search_view['res_id']            
        }
        return value

crm_bug_assign_wizard()
