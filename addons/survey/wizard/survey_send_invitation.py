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

from openerp import addons, netsvc, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _


class survey_send_invitation(osv.osv_memory):
    _name = 'survey.send.invitation'
    _columns = {
        'partner_ids': fields.many2many('res.partner','survey_res_partner','partner_id',\
                                'survey_id', "Answer", required=1),
        'send_mail': fields.boolean('Send Mail for New User'),
        'send_mail_existing': fields.boolean('Send Reminder for Existing User'),
        'mail_subject': fields.char('Subject', size=256),
        'mail_subject_existing': fields.char('Subject', size=256),
        'mail_from': fields.char('From', size=256, required=1),
        'mail': fields.text('Body')
    }

    _defaults = {
        'send_mail': lambda *a: 1,
        'send_mail_existing': lambda *a: 1,
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
        survey_id = 0
        for sur in survey_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            name += "\n --> " + sur.title + "\n"
            if sur.state != 'open':
                msg +=  sur.title + "\n"
            data['mail_subject'] = _("Invitation for %s") % (sur.title)
            data['mail_subject_existing'] = _("Invitation for %s") % (sur.title)
            data['mail_from'] = sur.responsible_id.email
            survey_id = sur.id
        if msg:
            raise osv.except_osv(_('Warning!'), _('The following surveys are not in open state: %s') % msg)
        data['mail'] = _('''
Hello %%(name)s, \n\n
Would you please spent some of your time to fill-in our survey: \n%s\n
You can access this survey with the following parameters:
 URL: %s
 Your login ID: %%(login)s\n
 Your password: %%(passwd)s\n
\n\n
Thanks,''') % (
            name, 
            self.pool.get('ir.config_parameter').get_param(
                cr, uid, 'web.base.url', default='http://localhost:8069',
                context=context)
                + '#id=%d&view_type=form&model=survey' % survey_id)
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
        group_id = model_data_obj.get_object_reference(
                cr, uid, 'base', 'group_survey_invitee')[1]

        act_id = self.pool.get('ir.actions.act_window')
        act_id = act_id.search(cr, uid, [('res_model', '=' , 'survey.name.wiz'), \
                        ('view_type', '=', 'form')])
        out = "login,password\n"
        skipped = 0
        existing = ""
        created = ""
        error = ""
        new_user = []
        attachments = {}
        current_sur = survey_ref.browse(cr, uid, context.get('active_id'), context=context)
        exist_user = current_sur.invited_user_ids
        if exist_user:
            for use in exist_user:
                new_user.append(use.id)
        for id in survey_ref.browse(cr, uid, survey_ids):
            service = netsvc.LocalService('report.survey.form');
            (result, format) = service.create(cr, uid, [id.id], {}, {})
            
            attachments[id.title +".pdf"] = result

        for partner in self.pool.get('res.partner').browse(cr, uid, partner_ids):
            if not partner.email:
                skipped+= 1
                continue
            user = user_ref.search(cr, uid, [('partner_id', "=", partner.id)])
            if user:
                if user[0] not in new_user:
                    new_user.append(user[0])
                user = user_ref.browse(cr, uid, user[0])
                user_ref.write(cr, uid, user.id, {'survey_id':[[6, 0, survey_ids]]})
                mail = record['mail']%{'login':partner.email, 'passwd':user.password, \
                                            'name' : partner.name}
                if record['send_mail_existing']:
                    vals = {
                        'state': 'outgoing',
                        'subject': record['mail_subject_existing'],
                        'body_html': '<pre>%s</pre>' % mail,
                        'email_to': partner.email,
                        'email_from': record['mail_from'],
                    }
                    self.pool.get('mail.mail').create(cr, uid, vals, context=context)
                    existing+= "- %s (Login: %s,  Password: %s)\n" % (user.name, partner.email, \
                                                                      user.password)
                continue

            passwd= self.genpasswd()
            out+= partner.email + ',' + passwd + '\n'
            mail= record['mail'] % {'login' : partner.email, 'passwd' : passwd, 'name' : partner.name}
            if record['send_mail']:
                vals = {
                        'state': 'outgoing',
                        'subject': record['mail_subject'],
                        'body_html': '<pre>%s</pre>' % mail,
                        'email_to': partner.email,
                        'email_from': record['mail_from'],
                }
                if attachments:
                    vals['attachment_ids'] = [(0,0,{'name': a_name,
                                                    'datas_fname': a_name,
                                                    'datas': str(a_content).encode('base64')})
                                                    for a_name, a_content in attachments.items()]
                ans = self.pool.get('mail.mail').create(cr, uid, vals, context=context)
                if ans:
                    res_data = {'name': partner.name or _('Unknown'),
                                'login': partner.email,
                                'email': partner.email,
                                'partner_id': partner.id,
                                'password': passwd,
                                'address_id': partner.id,
                                'groups_id': [[6, 0, [group_id]]],
                                'action_id': act_id[0],
                                'survey_id': [[6, 0, survey_ids]],
                                'partner_id': partner.id,
                                'tz': context.get('tz'),
                               }
                    user = user_ref.create(cr, uid, res_data)
                    if user not in new_user:
                        new_user.append(user)
                    created+= "- %s (Login: %s,  Password: %s)\n" % (partner.name or _('Unknown'),\
                                                                      partner.email, passwd)
                else:
                    error+= "- %s (Login: %s,  Password: %s)\n" % (partner.name or _('Unknown'),\
                                                                    partner.email, passwd)

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
            note += 'Email not send successfully:\n====================\n%s\n' % (error)
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
