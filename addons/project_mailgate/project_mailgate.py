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

import binascii
from osv import fields, osv
from tools.translate import _
import tools

class project_tasks(osv.osv):
    _inherit = 'project.task'

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None: custom_values = {}
        custom_values.update({
            'name': subject,
            'planned_hours': 0.0,
            'subject': msg.get('subject'),
        })
        return super(project_tasks,self).message_new(cr, uid, msg, custom_values=custom_values, context=context)

    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the task according to the email.
        """
        if update_vals is None: update_vals = {}
        act = False
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
                        update_vals[field] = float(res.group(2).lower())
                    except (ValueError, TypeError):
                        pass
                elif match.lower() == 'state' \
                        and res.group(2).lower() in ['cancel','close','draft','open','pending']:
                    act = 'do_%s' % res.group(2).lower()
        if act:
            getattr(self,act)(cr, uid, ids, context=context)
        return super(project_tasks,self).message_update(cr, uid, msg, update_vals=update_vals, context=context)

    def message_thread_followers(self, cr, uid, ids, context=None):
        followers = super(project_tasks,self).message_thread_followers(cr, uid, ids, context=context)
        for task in self.browse(cr, uid, followers.keys(), context=context):
            task_followers = set(followers[task.id])
            task_followers.add(task.user_id.email)
            followers[task.id] = filter(None, task_followers)
        return followers


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
