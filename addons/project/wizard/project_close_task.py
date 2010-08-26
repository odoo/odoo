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

from osv import fields, osv
from tools.translate import _
from tools import email_send as email

class project_close_task(osv.osv_memory):
    """
    Close Task
    """
    _name = "close.task"
    _description = "Project Close Task"
    _columns = {
        'manager_email': fields.char('Manager E-Mail ID', size=64, help="Email Address of Project's Manager"),
        'partner_email': fields.char('Partner E-Mail ID', size=64, help="Email Address of Partner"),
        'description': fields.text('Description'),
    }

    def _get_manager_email(self, cr, uid, context=None):
        if context is None:
            context = {}
        email = ''
        if context.get('send_manager', False) and ('task_id' in context):
            project_id = self.pool.get('project.task').read(cr, uid, context['task_id'], ['project_id'])['project_id'][0]
            project = self.pool.get('project.project').browse(cr, uid, project_id)
            manager_id = project.user_id or False
            if manager_id and manager_id.user_email:
                email = manager_id.user_email
        return email

    def _get_partner_email(self, cr, uid, context=None):
        if context is None:
            context = {}
        email = ''
        if context.get('send_partner', False) and ('task_id' in context):
            task = self.pool.get('project.task').browse(cr, uid, context['task_id'])
            partner_id = task.partner_id or task.project_id.partner_id
            if partner_id and len(partner_id.address) and partner_id.address[0].email:
                email = partner_id.address[0].email
        return email

    def _get_desc(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'task_id' in context:
            task = self.pool.get('project.task').browse(cr, uid, context['task_id'])
            return task.description or task.name
        return ''

    _defaults = {
       'manager_email': _get_manager_email,
       'partner_email': _get_partner_email,
    }

    def close(self, cr, uid, ids, context=None):
        data = self.read(cr,uid,ids)[0]
        task_pool = self.pool.get('project.task')
        user_name = self.pool.get('res.users').browse(cr, uid, uid).name
        description = _("Closed By ") + user_name + _(" At ") + time.strftime('%Y-%m-%d %H:%M:%S')
        description += "\n" + "=======================" + "\n"  + data['description']
        if 'task_id' in context:
            task = task_pool.browse(cr, uid, context['task_id'])
            description = task.description + "\n\n" + description
            task_pool.write(cr, uid, [task.id], {
                    'description': description,
                    'state': 'done', 
                    'date_end':time.strftime('%Y-%m-%d %H:%M:%S'), 
                    'remaining_hours': 0.0
            })
        return {}

    def confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not 'task_id' in context:
            return {}
        close_task = self.read(cr, uid, ids[0], [])
        to_adr = []
        description = close_task['description']

        if 'task_id' in context:
            if context.get('send_manager', False) and not close_task.get('manager_email', False):
                raise osv.except_osv(_('Error'), _("Please specify the email address of Project Manager."))

            elif context.get('send_partner', False) and not close_task.get('partner_email', False):
                raise osv.except_osv(_('Error'), _("Please specify the email address of partner."))

            else:
                task_obj = self.pool.get('project.task')
                task = task_obj.browse(cr, uid, context['task_id'], context=context)
                project = task.project_id
                subject = "Task '%s' closed" % task.name
                if task.user_id and task.user_id.address_id and task.user_id.address_id.email:
                    from_adr = task.user_id.address_id.email
                    signature = task.user_id.signature
                else:
                    raise osv.except_osv(_('Error'), _("Couldn't send mail because your email address is not configured!"))
                val = {
                        'name': task.name,
                        'user_id': task.user_id.name,
                        'task_id': "%d/%d" % (project.id, task.id),
                        'date_start': task.date_start,
                        'date_end': task.date_end,
                        'state': task.state
                }

                header = (project.warn_header or '') % val
                footer = (project.warn_footer or '') % val
                body = u'%s\n%s\n%s\n\n-- \n%s' % (header, description, footer, signature)
                to_adr.append(context.get('send_manager', '') and close_task.get('manager_email', '') or '')
                to_adr.append(context.get('send_partner', '') and close_task.get('partner_email', '') or '')
                mail_id = email(from_adr, to_adr, subject, body.encode('utf-8'), email_bcc=[from_adr])
                if not mail_id:
                    raise osv.except_osv(_('Error'), _("Couldn't send mail! Check the email ids and smtp configuration settings"))
                task_obj.write(cr, uid, [task.id], {'state': 'done', 'date_end':time.strftime('%Y-%m-%d %H:%M:%S'), 'remaining_hours': 0.0})
                message = _('Task ') + " '" + task.name + "' "+ _("is Done.")
                self.log(cr, uid, task.id, message)

        return {}

project_close_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
