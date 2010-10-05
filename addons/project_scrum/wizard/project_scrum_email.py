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

from lxml import etree
from osv import fields, osv
from tools.translate import _
from datetime import datetime

class project_scrum_email(osv.osv_memory):
    _name = 'project.scrum.email'

    def _get_master_email(self,cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False
#        res='master@gmail.com'
        if active_id:
            res = self.pool.get('project.scrum.meeting').browse(cr,uid,active_id,context=context).sprint_id.scrum_master_id.user_email
        return res

    def _get_owner_email(self,cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False
#        res='owner@gmail.com'
        if active_id:
            res = self.pool.get('project.scrum.meeting').browse(cr, uid,active_id,context=context).sprint_id.product_owner_id.user_email
        return res

    def _get_subject(self,cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False

#        res='owner@gmail.com'
        if active_id:
            res1= self.pool.get('project.scrum.meeting').browse(cr,uid,active_id).date
            res=" Scrum Meeting  of " + res1
            print res
        return res

    def _get_message(self,cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False

#        res='owner@gmail.com'
        if active_id:

            res1= self.pool.get('project.scrum.meeting').browse(cr,uid,active_id).date
            cnv_date = datetime.strptime(res1,'%Y-%m-%d')
            weekfordate=datetime.strftime(cnv_date,'%W')
            res2= self.pool.get('project.scrum.meeting').browse(cr,uid,active_id).sprint_id.project_id.name
            res=" Scrum Meeting  of "+res1+" on Sprint Week "+weekfordate+" of Project "+res2
        return res


    _columns = {
        'scrum_master_id': fields.char('Scrum Master Email', size=220,help="The person who is maintains the processes for the product"),
        'product_owner_id': fields.char('Product Owner Email', size=220,help="The person who is responsible for the product"),
        'subject':fields.char('Subject',size=220),
        'message':fields.text('Message'),

               }

    _defaults = {
        'scrum_master_id': _get_master_email,
        'product_owner_id': _get_owner_email,
        'subject': _get_subject,
        'message': _get_message,

    }

#    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
#        res = super(project_task_reevaluate, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu=submenu)
#        users_pool = self.pool.get('res.users')
#        time_mode = users_pool.browse(cr, uid, uid, context).company_id.project_time_mode_id
#        time_mode_name = time_mode and time_mode.name or 'Hours'
#        if time_mode_name in ['Hours','Hour']:
#            return res
#
#        eview = etree.fromstring(res['arch'])
#
#        def _check_rec(eview):
#            if eview.attrib.get('widget','') == 'float_time':
#                eview.set('widget','float')
#            for child in eview:
#                _check_rec(child)
#            return True
#
#        _check_rec(eview)
#
#        res['arch'] = etree.tostring(eview)
#
#        for field in res['fields']:
#            if 'Hours' in res['fields'][field]['string']:
#                res['fields'][field]['string'] = res['fields'][field]['string'].replace('Hours',time_mode_name)
#        return res

#    def compute_hours(self, cr, uid, ids, context=None):
#        if context is None:
#            context = {}
#        data = self.browse(cr, uid, ids, context=context)[0]
#        task_pool = self.pool.get('project.task')
#        task_id = context.get('active_id', False)
#        if task_id:
#            task_pool.write(cr, uid, task_id, {'remaining_hours': data.remaining_hours})
#            if context.get('button_reactivate', False):
#                task_pool.do_reopen(cr, uid, [task_id], context=context)
#        return {}
project_scrum_email()
