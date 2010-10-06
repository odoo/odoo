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
import tools

class project_scrum_email(osv.osv_memory):
    _name = 'project.scrum.email'

    def _get_master_email(self,cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False
        if active_id:
            res = self.pool.get('project.scrum.meeting').browse(cr,uid,active_id,context=context).sprint_id.scrum_master_id.user_email
        return res

    def _get_owner_email(self,cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False
        if active_id:
            res = self.pool.get('project.scrum.meeting').browse(cr, uid,active_id,context=context).sprint_id.product_owner_id.user_email
        return res

    def _get_subject(self,cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False

        if active_id:
            res1= self.pool.get('project.scrum.meeting').browse(cr,uid,active_id).date
            res=" Scrum Meeting  of " + res1
        return res

    def _get_message(self,cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False

        if active_id:
            res1= self.pool.get('project.scrum.meeting').browse(cr,uid,active_id).date
            sprint_name= self.pool.get('project.scrum.meeting').browse(cr,uid,active_id).sprint_id.name
            cnv_date = datetime.strptime(res1,'%Y-%m-%d')
            weekfordate=datetime.strftime(cnv_date,'%W')
            res2= self.pool.get('project.scrum.meeting').browse(cr,uid,active_id).sprint_id.project_id.name
            res3='Hello  , \n    I am sending you Daily Meeting Details of date  '+res1+'  for the Sprint  '+sprint_name
            res=res3+" of Project "+res2
        return res


    _columns = {
        'scrum_master_id': fields.char('Scrum Master Email', size=64,help="The person who is maintains the processes for the product"),
        'product_owner_id': fields.char('Product Owner Email', size=64,help="The person who is responsible for the product"),
        'subject':fields.char('Subject',size=64),
        'message':fields.text('Message'),

               }

    _defaults = {
        'scrum_master_id': _get_master_email,
        'product_owner_id': _get_owner_email,
        'subject': _get_subject,
        'message': _get_message,

    }


    def button_send_scrum_email(self, cr, uid, ids, context=None):
        if context is None:
            context={}

        active_id = context.get('active_id', False)
        scrum_obj=self.pool.get('project.scrum.meeting').browse(cr, uid,active_id,context=context)

#        wizard data
        meeting_wizard_id=self.browse(cr,uid,ids,context=context)[0]
        scrum_master_email=meeting_wizard_id.scrum_master_id
        product_owner_email=meeting_wizard_id.product_owner_id
        mail_subject=meeting_wizard_id.subject
        mail_message=meeting_wizard_id.message



#        Record Data
        if active_id:
            scrum_master_name=scrum_obj.sprint_id.scrum_master_id.name
            product_owner_name=scrum_obj.sprint_id.product_owner_id.name
            last_meeting = scrum_obj.question_yesterday
            if not last_meeting:
                last_meeting=""
            next_meeting = scrum_obj.question_today
            if not next_meeting:
                next_meeting=""
            block_meeting = scrum_obj.question_blocks
            if not block_meeting:
                block_meeting=""
            backlog_accurate = scrum_obj.question_backlog
            if not backlog_accurate:
                backlog_accurate=""
            mail_date=scrum_obj.date
            sprint_name=scrum_obj.sprint_id.name
            task_record_list=[]
            for task_assign in scrum_obj.task_ids:
                task_record=task_assign.name
                task_record_list.append(task_record)

#         Email
        if scrum_master_email:
            if product_owner_email:
                send_owner = self.email_send(cr,uid, ids,product_owner_email,mail_subject,mail_message,
                                             last_meeting,next_meeting,block_meeting,backlog_accurate,
                                             task_record_list,product_owner_name,
                                             mail_date,sprint_name,active_id)
                if not send_owner:
                    raise osv.except_osv(_('Error !'), _(' Email Not send to the product owner !' ))

            else:
                raise osv.except_osv(_('Error !'), _('Please provide email address for product owner defined on sprint.'))
            send_master = self.email_send(cr, uid, ids,scrum_master_email,mail_subject,mail_message,
                                          last_meeting,next_meeting,block_meeting,backlog_accurate,
                                          task_record_list,scrum_master_name,mail_date,
                                          sprint_name,active_id)
            if not send_master:
                    raise osv.except_osv(_('Error !'), _(' Email Not send to the scrum master !' ))
            else:
                return {'type':'ir.actions.act_window_close' }
        else:
            raise osv.except_osv(_('Error !'), _('Please provide email address for scrum master defined on sprint.'))

        return True

    def email_send(self, cr, uid, ids, email,mail_subject,mail_message,
                   last_meeting,next_meeting,block_meeting,backlog_accurate,
                   task_record_list,user_own_name,mail_date,sprint_name,active_id,
                   context=None):
        if context is None:
            context = {}
        email_from = tools.config.get('email_from', False)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        user_email = email_from or user.address_id.email
        sub_name = mail_subject

        body ="\n"+mail_message+"\n"
        body += "\n"+ _('What did you do since the last meeting?')+ '\n_______________________\n'
        body +="\n"+last_meeting+"\n"
        body +="\n" +_("What do you plan to do till the next meeting?")+ '\n_______________________ \n'
        body +="\n"+next_meeting+"\n"
        body +="\n"+ _('Are there anything blocking you?') +'\n_______________________ \n'
        body +="\n"+block_meeting+"\n"
        body +="\n"+ _('Are your Sprint Backlog estimate accurate ?') +'\n_______________________ \n'
        body +="\n"+backlog_accurate+"\n"
        body += "\n"+ _('Tasks Summary:')+ '\n_______________________'
        str=""
        for taskassign in task_record_list:
            str=str +"\n"
            str  =str + taskassign
        body +=str
        body += "\n\n"+_('Thank you')+",\n"+ user.name

        flag = tools.email_send(user_email,[email], sub_name, body, reply_to=None,openobject_id=active_id)
        if not flag:
            return False
        return True

project_scrum_email()
