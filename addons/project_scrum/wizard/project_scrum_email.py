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
from datetime import datetime
import tools

class project_scrum_email(osv.osv_memory):
    _name = 'project.scrum.email'

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        @return : default values of fields.
        """
        if context is None:
            context = {}
        meeting_pool = self.pool.get('project.scrum.meeting')
        record_ids = context and context.get('active_ids', []) or []
        res = super(project_scrum_email, self).default_get(cr, uid, fields, context=context)
        for meeting in meeting_pool.browse(cr, uid, record_ids, context=context):
            sprint = meeting.sprint_id
            if 'scrum_master_email' in fields:
                res.update({'scrum_master_email': sprint.scrum_master_id and sprint.scrum_master_id.user_email or False})
            if 'product_owner_email' in fields:
                res.update({'product_owner_email': sprint.product_owner_id and sprint.product_owner_id.user_email or False})
            if 'subject' in fields:
                subject = _("Scrum Meeting : %s") %(meeting.date)
                res.update({'subject': subject})
            if 'message' in fields:
                message = _("Hello  , \nI am sending you Scrum Meeting : %s for the Sprint  '%s' of Project '%s'") %(meeting.date, sprint.name, sprint.project_id.name)
                res.update({'message': message})
        return res

    _columns = {
        'scrum_master_email': fields.char('Scrum Master Email', size=64, help="Email Id of Scrum Master"),
        'product_owner_email': fields.char('Product Owner Email', size=64, help="Email Id of Product Owner"),
        'subject':fields.char('Subject', size=64),
        'message':fields.text('Message'),

    }

    def button_send_scrum_email(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        email_message_obj = self.pool.get('email.message')
        active_id = context.get('active_id', False)
        scrum_meeting_pool = self.pool.get('project.scrum.meeting')
        user_pool = self.pool.get('res.users')
        meeting = scrum_meeting_pool.browse(cr, uid, active_id, context=context)

#        wizard data
        data_id = ids and ids[0] or False
        if not data_id or not active_id:
            return False
        data = self.browse(cr, uid, data_id, context=context)

        email_from = tools.config.get('email_from', False)
        user = user_pool.browse(cr, uid, uid, context=context)
        user_email = email_from or user.address_id.email

        body = "%s\n" %(data.message)
        body += "\n%s\n" %_('Tasks since yesterday')
        body += "_______________________\n"
        body += "\n%s\n" %(meeting.question_yesterday or _('None'))
        body += "\n%s\n" %_("Task for Today")
        body += "_______________________ \n"
        body += "\n%s\n" %(meeting.question_today or _('None'))
        body += "\n%s\n" % _('Blocking points encountered:')
        body += "_______________________ \n"
        body += "\n%s\n" %(meeting.question_blocks or _('None'))
        body += "\n%s\n%s" %(_('Thank you,'), user.name)
        if user.signature:
            body += "\n%s" %(user.signature)
        if data.scrum_master_email == data.product_owner_email:
            data.product_owner_email = False
        if data.scrum_master_email:
            email_message_obj.schedule_with_attach(cr, uid, user_email, [data.scrum_master_email], data.subject, body, model='project.scrum.email', reply_to=user_email)
        if data.product_owner_email:
            email_message_obj.schedule_with_attach(cr, uid, user_email, [data.product_owner_email], data.subject, body, model='project.scrum.email', reply_to=user_email)
        return {'type': 'ir.actions.act_window_close'}
project_scrum_email()
