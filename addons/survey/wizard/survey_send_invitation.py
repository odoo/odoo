# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import time
from random import choice
import string
import os
import datetime
import socket

from osv import fields
from osv import osv
import tools
from tools.translate import _
import netsvc
import addons


class survey_send_invitation(osv.osv_memory):
    _name = 'survey.send.invitation'
    _columns = {
        'partner_ids': fields.many2many('res.partner','survey_res_partner','partner_id',\
                                'survey_id', "Answer", required=1),
        'send_mail': fields.boolean('Send mail for new user'),
        'send_mail_existing': fields.boolean('Send reminder for existing user'),
        'mail_subject': fields.char('Subject', size=256),
        'mail_subject_existing': fields.char('Subject', size=256),
        'mail_from': fields.char('From', size=256, required=1),
        'mail': fields.text('Body')
    }

    _defaults = {
        'send_mail': lambda *a: 1,
        'send_mail_existing': lambda *a: 1,
        'mail_subject': lambda *a: "Invitation",
        'mail_subject_existing': lambda *a: "Invitation",
        'mail_from': lambda *a: tools.config['email_from']
    }

    def genpasswd(self):
        chars = string.letters + string.digits
        return ''.join([choice(chars) for i in range(6)])

    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        data = super(survey_send_invitation, self).default_get(cr, uid, fields_list, context)
        survey_obj = self.pool.get('survey')
        msg = ""
        name = ""
        for sur in survey_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            name += "\t --> " + sur.title + "\n"
            if sur.state != 'open':
                msg +=  sur.title + "\n"
        if msg:
            raise osv.except_osv(_('Warning !'), _('%sSurvey is not in open state') % msg)
        data['mail'] = '''Hello %(name)s, \n\n We are inviting you for following survey. \
                    \n  ''' + name + '''\n Your login ID: %(login)s, Your password: %(passwd)s
                    \n link :- http://'''+ str(socket.gethostname()) + ''':8080 \n\n Thanks,'''
        return data

    def create_report(self, cr, uid, res_ids, report_name=False, file_name=False):
        if not report_name or not res_ids:
            return (False, Exception('Report name and Resources ids are required !!!'))
        try:
            ret_file_name = addons.get_module_resource('survey', 'report') + file_name + '.pdf'
            service = netsvc.LocalService(report_name);
            (result, format) = service.create(cr, uid, res_ids, {}, {})
            fp = open(ret_file_name, 'wb+');
            fp.write(result);
            fp.close();
        except Exception,e:
            print 'Exception in create report:',e
            return (False, str(e))
        return (True, ret_file_name)


    def action_send(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        record = self.read(cr, uid, ids, [],context=context)
        survey_ids =  context.get('active_ids', [])
        record = record and record[0]
        partner_ids = record['partner_ids']
        user_ref= self.pool.get('res.users')
        survey_ref= self.pool.get('survey')
        mail_message = self.pool.get('mail.message')

        model_data_obj = self.pool.get('ir.model.data')
        group_id = model_data_obj._get_id(cr, uid, 'base', 'group_survey_user')
        group_id = model_data_obj.browse(cr, uid, group_id, context=context).res_id

        act_id = self.pool.get('ir.actions.act_window')
        act_id = act_id.search(cr, uid, [('res_model', '=' , 'survey.name.wiz'), \
                        ('view_type', '=', 'form')])
        out = "login,password\n"
        skipped = 0
        existing = ""
        created = ""
        error = ""
        user_exists = False
        new_user = []
        attachments = {}
        current_sur = survey_ref.browse(cr, uid, context.get('active_id'), context=context)
        exist_user = current_sur.invited_user_ids
        if exist_user:
            for use in exist_user:
                new_user.append(use.id)
        for id in survey_ref.browse(cr, uid, survey_ids):
            report = self.create_report(cr, uid, [id.id], 'report.survey.form', id.title)
            file = open(addons.get_module_resource('survey', 'report') + id.title +".pdf")
            file_data = ""
            while 1:
                line = file.readline()
                file_data += line
                if not line:
                    break
            file.close()
            attachments[id.title +".pdf"] = file_data
            os.remove(addons.get_module_resource('survey', 'report') + id.title +".pdf")

        for partner in self.pool.get('res.partner').browse(cr, uid, partner_ids):
            for addr in partner.address:
                if not addr.email:
                    skipped+= 1
                    continue
                user = user_ref.search(cr, uid, [('login', "=", addr.email)])
                if user:
                    if user[0] not in new_user:
                        new_user.append(user[0])
                    user = user_ref.browse(cr, uid, user[0])
                    user_ref.write(cr, uid, user.id, {'survey_id':[[6, 0, survey_ids]]})
                    mail = record['mail']%{'login':addr.email, 'passwd':user.password, \
                                                'name' : addr.name}
                    if record['send_mail_existing']:
                        mail_message.schedule_with_attach(cr, uid, record['mail_from'], [addr.email] , \
                                         record['mail_subject_existing'] , mail, context=context)
                        existing+= "- %s (Login: %s,  Password: %s)\n" % (user.name, addr.email, \
                                                                          user.password)
                    continue

                passwd= self.genpasswd()
                out+= addr.email + ',' + passwd + '\n'
                mail= record['mail'] % {'login' : addr.email, 'passwd' : passwd, 'name' : addr.name}
                if record['send_mail']:
                    ans = mail_message.schedule_with_attach(cr, uid, record['mail_from'], [addr.email], \
                                           record['mail_subject'], mail, attachments=attachments, context=context)
                    if ans:
                        res_data = {'name': addr.name or 'Unknown',
                                    'login': addr.email,
                                    'password': passwd,
                                    'address_id': addr.id,
                                    'groups_id': [[6, 0, [group_id]]],
                                    'action_id': act_id[0],
                                    'survey_id': [[6, 0, survey_ids]]
                                   }
                        user = user_ref.create(cr, uid, res_data)
                        if user not in new_user:
                            new_user.append(user)
                        created+= "- %s (Login: %s,  Password: %s)\n" % (addr.name or 'Unknown',\
                                                                          addr.email, passwd)
                    else:
                        error+= "- %s (Login: %s,  Password: %s)\n" % (addr.name or 'Unknown',\
                                                                        addr.email, passwd)

        new_vals = {}
        new_vals.update({'invited_user_ids':[[6,0,new_user]]})
        survey_ref.write(cr, uid, context.get('active_id'),new_vals)
        note= ""
        if created:
            note += 'Created users:\n%s\n\n' % (created)
        if existing:
            note +='Already existing users:\n%s\n\n' % (existing)
        if skipped:
            note += "%d contacts where ignored (an email address is missing).\n\n" % (skipped)
        if error:
            note += 'E-Mail not send successfully:\n====================\n%s\n' % (error)
        context.update({'note' : note})
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.send.invitation.log',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
survey_send_invitation()

class survey_send_invitation_log(osv.osv_memory):
    _name = 'survey.send.invitation.log'
    _columns = {
        'note' : fields.text('Log', readonly=1)
    }

    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        data = super(survey_send_invitation_log, self).default_get(cr, uid, fields_list, context)
        data['note'] = context.get('note', '')
        return data

survey_send_invitation_log()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
