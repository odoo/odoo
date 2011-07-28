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
import binascii


class project_tasks(osv.osv):
    _name = "project.task"
    _inherit = ['mailgate.thread', 'project.task']

    _columns={
                'message_ids': fields.one2many('mailgate.message', 'res_id', 'Messages', domain=[('model', '=', _name)], readonly=True),
              }

    def message_new(self, cr, uid, msg, context=None):
#        """
#        Automatically calls when new email message arrives
#
#        @param self: The object pointer
#        @param cr: the current row, from the database cursor,
#        @param uid: the current user’s ID for security checks
#        """
        mailgate_obj = self.pool.get('email.server.tools')
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
        res = mailgate_obj.get_partner(cr, uid, msg_from)
        if res:
            data.update(res)
        res = self.create(cr, uid, data)

        attachments = msg.get('attachments', [])
        for attachment in attachments or []:
            data_attach = {
                'name': attachment,
                'datas': binascii.b2a_base64(str(attachments.get(attachment))),
                'datas_fname': attachment,
                'description': 'Mail attachment',
                'res_model': self._name,
                'res_id': res,
            }
            self.pool.get('ir.attachment').create(cr, uid, data_attach)

        return res

    def message_update(self, cr, uid, id, msg, data={}, default_act='pending'):
        mailgate_obj = self.pool.get('email.server.tools')
        msg_actions, body_data = mailgate_obj.msg_act_get(msg)
        data.update({
            'description': body_data,
        })
        act = 'do_'+default_act
        if 'state' in msg_actions:
            if msg_actions['state'] in ['draft', 'close', 'cancel', 'open', 'pending']:
                act = 'do_' + msg_actions['state']

        for k1, k2 in [('cost', 'planned_hours')]:
            try:
                data[k2] = float(msg_actions[k1])
            except:
                pass

        if 'priority' in msg_actions:
            if msg_actions['priority'] in ('1', '2', '3', '4', '5'):
                data['priority'] = msg_actions['priority']

        self.write(cr, uid, [id], data)
        getattr(self, act)(cr, uid, [id])
        return True

    def message_followers(self, cr, uid, ids, context=None):
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

    def _history(self, cr, uid, cases, keyword, history=False, subject=None, email=False, details=None, email_from=False, message_id=False, attach=[], context=None):
        mailgate_pool = self.pool.get('mailgate.thread')
        return mailgate_pool.history(cr, uid, cases, keyword, history=history,\
                                       subject=subject, email=email, \
                                       details=details, email_from=email_from,\
                                       message_id=message_id, attach=attach, \
                                       context=context)

    def do_draft(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_draft(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self._history(cr, uid, tasks, _('Draft'), context=context)
        return res

    def do_open(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_open(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self._history(cr, uid, tasks, _('Open'), context=context)
        return res

    def do_pending(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_pending(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self._history(cr, uid, tasks, _('Pending'), context=context)
        return res

    def do_close(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_close(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        for task in tasks:
            if task.state == 'done':
                self._history(cr, uid, tasks, _('Done'), context=context)
        return res

    def do_cancel(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_cancel(cr, uid, ids, context=context)
        tasks = self.browse(cr, uid, ids, context=context)
        self._history(cr, uid, tasks, _('Cancel'), context=context)
        return res

project_tasks()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
