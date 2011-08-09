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
import tools
import binascii


class project_tasks(osv.osv):
    _name = "project.task"
    _inherit = ['mail.thread','project.task']

    _columns={
                'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', domain=[('model','=',_name)], readonly=True),
              }

    def message_new(self, cr, uid, msg, context=None):
#        """
#        Automatically calls when new email message arrives
#
#        @param self: The object pointer
#        @param cr: the current row, from the database cursor,
#        @param uid: the current user’s ID for security checks
#        """
        thread_obj = self.pool.get('email.thread')
        subject = msg.get('subject')
        body = msg.get('body')
        msg_from = msg.get('from')
        #TODO map email priority with openerp task priority
        priority = msg.get('priority') 

        data = {
            'name': subject,
            'description': body,
            'planned_hours': 0.0,
        }
        res = thread_obj.get_partner(cr, uid, msg_from)
        if res:
            data.update(res)
        res_id = self.create(cr, uid, data, context)

        attachments = msg.get('attachments', {})
        for attachment in attachments:
            data_attach = {
                'name': attachment,
                'datas': binascii.b2a_base64(str(attachments.get(attachment))),
                'datas_fname': attachment,
                'description': 'Mail attachment',
                'res_model': self._name,
                'res_id': res,
            }
            self.pool.get('ir.attachment').create(cr, uid, data_attach, context)
        self.history(cr, uid, [res_id], _('receive'), history=True,
                            subject = msg.get('subject'),
                            email = msg.get('to'),
                            details = msg.get('body'),
                            email_from = msg.get('from'),
                            email_cc = msg.get('cc'),
                            message_id = msg.get('message-id'),
                            references = msg.get('references', False) or msg.get('in-reply-to', False),
                            attach = attachments,
                            email_date = msg.get('date'),
                            body_html= msg.get('body_html'),
                            sub_type = msg.get('sub_type'),
                            headers = msg.get('headers'),
                            priority = msg.get('priority'),
                            context = context)
        return res_id

    def message_update(self, cr, uid, ids, msg, data={}, default_act='pending'):
        data.update({
            'description': msg['body_text'],
        })
        act = 'do_'+default_act

        maps = { 
            'cost':'planned_hours',
        }
        for line in msg['body'].split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res:
                match = res.group(1).lower()
                field = maps.get(match)
                if field:
                    try:
                        data[field] = float(res.group(2).lower())
                    except (ValueError, TypeError):
                        pass
                elif match.lower() == 'state' \
                        and res.group(2).lower() in ['cancel','close','draft','open','pending']:
                    act = 'do_%s' % res.group(2).lower()

        self.write(cr, uid, ids, data, context=context)
        getattr(self,act)(cr, uid, ids, context=context)

        attachments = msg.get('attachments', {})
        self.history(cr, uid, ids, _('receive'), history=True,
                            subject = msg.get('subject'),
                            email = msg.get('to'),
                            details = msg.get('body'),
                            email_from = msg.get('from'),
                            email_cc = msg.get('cc'),
                            message_id = msg.get('message-id'),
                            references = msg.get('references', False) or msg.get('in-reply-to', False),
                            attach = attachments,
                            email_date = msg.get('date'),
                            body_html= msg.get('body_html'),
                            sub_type = msg.get('sub_type'),
                            headers = msg.get('headers'),
                            priority = msg.get('priority'),
                            context = context)
        return True

    def thread_followers(self, cr, uid, ids, context=None):
        res = []
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        for task in self.browse(cr, uid, select, context=context):
            user_email = (task.user_id and task.user_id.user_email) or False
            res += [(user_email, False, False, task.priority)]
        if isinstance(ids, (str, int, long)):
            return len(res) and res[0] or False
        return res

    def msg_send(self, cr, uid, id, *args, **argv):
        return True

    def do_draft(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_draft(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self.history(cr, uid, tasks, _('Draft'), context=context)
        return res

    def do_open(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_open(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self.history(cr, uid, tasks, _('Open'), context=context)
        return res

    def do_pending(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_pending(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self.history(cr, uid, tasks, _('Pending'), context=context)
        return res

    def do_close(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_close(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        for task in tasks:
            if task.state == 'done':
                self.history(cr, uid, tasks, _('Done'), context=context)
        return res

    def do_cancel(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_cancel(cr, uid, ids, context=context)
        tasks = self.browse(cr, uid, ids, context=context)
        self.history(cr, uid, tasks, _('Cancel'), context=context)
        return res

project_tasks()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
