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
        'email': fields.char('E-Mails', size=64,),
        'description': fields.text('Description',),
               }

    def _get_email(self, cr, uid, context={}):
        email = ''
        if 'task_id' in context:
            task = self.pool.get('project.task').browse(cr, uid, context['task_id'])
            partner_id = task.partner_id or task.project_id.partner_id
            if partner_id and partner_id.address[0].email:
                email = partner_id.address[0].email
        return email

    def _get_desc(self, cr, uid, context={}):
        if 'task_id' in context:
            task = self.pool.get('project.task').browse(cr, uid, context['task_id'])
            return task.description or task.name
        return ''

    _defaults={
       'email': _get_email,
       'description': _get_desc,
               }

    def confirm(self, cr, uid, ids, context={}):
        if not 'task_id' in context:
            return {}
        close_task = self.read(cr, uid, ids[0], [])
        to_adr = close_task['email']
        description = close_task['description']
        if 'task_id' in context:
            for task in self.pool.get('project.task').browse(cr, uid, [context['task_id']], context=context):
                project = task.project_id
                subject = "Task '%s' closed" % task.name
                if task.user_id and task.user_id.address_id and task.user_id.address_id.email:
                    from_adr = task.user_id.address_id.email
                    signature = task.user_id.signature
                else:
                    raise osv.except_osv(_('Error'), _("Couldn't send mail because your email address is not configured!"))
                if to_adr:
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
                    email(from_adr, [to_adr], subject, body.encode('utf-8'), email_bcc=[from_adr])
                else:
                    raise osv.except_osv(_('Error'), _("Couldn't send mail because the contact for this task (%s) has no email address!") % contact.name)
        return {}

project_close_task()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: