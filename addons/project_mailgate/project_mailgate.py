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

    _columns = {
         'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', domain=[('model','=',_name)], readonly=True),
    }

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        res_id = super(project_tasks,self).message_new(cr, uid, msg, custom_values=custom_values, context=context)
        subject = msg.get('subject')
        body = msg.get('body_text')
        msg_from = msg.get('from')
        data = {
            'name': subject,
            'description': body,
            'planned_hours': 0.0,
        }
        data.update(self.message_partner_by_email(cr, uid, msg_from))
        self.write(cr, uid, [res_id], data, context)
        return res_id

    def message_update(self, cr, uid, ids, msg, data={}, default_act='pending'):
        data.update({
            'description': msg['body_text'],
        })
        act = 'do_'+default_act

        maps = { 
            'cost':'planned_hours',
        }
        for line in msg['body_text'].split('\n'):
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
        self.message_append_dict(cr, uid, [res_id], msg, context=context)
        return True

    def message_thread_followers(self, cr, uid, ids, context=None):
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

    def do_draft(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_draft(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self.message_append(cr, uid, tasks, _('Draft'), context=context)
        return res

    def do_open(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_open(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self.message_append(cr, uid, tasks, _('Open'), context=context)
        return res

    def do_pending(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_pending(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        self.message_append(cr, uid, tasks, _('Pending'), context=context)
        return res

    def do_close(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_close(cr, uid, ids, context)
        tasks = self.browse(cr, uid, ids, context=context)
        for task in tasks:
            if task.state == 'done':
                self.message_append(cr, uid, tasks, _('Done'), context=context)
        return res

    def do_cancel(self, cr, uid, ids, context=None):
        res = super(project_tasks, self).do_cancel(cr, uid, ids, context=context)
        tasks = self.browse(cr, uid, ids, context=context)
        self.message_append(cr, uid, tasks, _('Cancel'), context=context)
        return res

project_tasks()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
