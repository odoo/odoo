# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import time
import pooler
from random import choice
import string
import tools
from tools.translate import _
import tools
import os
import datetime
import netsvc
import socket

_survey_form = '''<?xml version="1.0"?>
<form string="Send Invitation">
    <separator string="Select Partner" colspan="4"/>
    <field name="partner_ids" nolabel="1"  colspan="4"/> /> 
    <separator colspan="4" string="Send mail for new user"/>
    <group cols="2" colspan="4">
        <field name="send_mail" nolabel="1"/>
        <field name="mail_subject"/>
        <newline/>
        <separator colspan="4" string="Send reminder for existing user"/>
        <field name="send_mail_existing" nolabel="1"/>
        <field name="mail_subject_existing"/>    
        <newline/>
    </group>
    <separator colspan="4"/>
    <group cols="2" colspan="4">
        <field name="mail_from" colspan="4"/>
    </group>
    <newline/>
    <separator string="Message" colspan="4"/>
    <field name="mail" nolabel="1" colspan="4"/>
</form>'''


_survey_fields = {
    'partner_ids': {'string':'Partner', 'type':'many2many', 'relation':'res.partner'},
    'send_mail': {'string':'Send mail for new user', 'type':'boolean', 'default':lambda * a: 1},
    'send_mail_existing': {'string':'Send reminder for existing user', 'type':'boolean', 'default':lambda * a: 1},
    'mail_subject': {'string':'Subject', 'type':'char', 'default':lambda * a: "New user account.", "size":256},
    'mail_subject_existing': {'string':'Subject', 'type':'char', 'default':lambda * a: "User account info.", "size":256},
    'mail_from': {'string':'From', 'type':'char', "size":256, 'required':True, 'default':lambda * a: tools.config['email_from']  },
    'mail': {'string':'Body', 'type':'text'},
    }

second_form = '''<?xml version="1.0"?>
<form string="User creation">
    <separator string="Results :" colspan="4"/>
    <field name="note" colspan="4" nolabel="1" width="300"/>
</form>'''
second_fields = {
    'note' : {'string':'Log', 'type':'text', 'readonly':1}
    }
def genpasswd():
    chars = string.letters + string.digits
    return ''.join([choice(chars) for i in range(6)])

def check_survey(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    survey_obj = pool.get('survey')
    msg = ""
    name = ""
    for sur in survey_obj.browse(cr, uid, data['ids']):
        name += "\t --> " + sur.title + "\n"
        if sur.state != 'open':
            msg += sur.title + "\n"
    if msg:
        raise  wizard.except_wizard(_('Attention!'), _('%sSurvey is not in open state') % msg)
    data['form']['mail'] = '''Hello %(name)s, \n\n We are inviting you for following survey. \
                \n  ''' + name + '''\n Your login ID: %(login)s, Your password: %(passwd)s
    \n link :- http://''' + str(socket.gethostname()) + ''':8080 \n\n Thanks,'''
    return data['form']

def send_mail(self, cr, uid, data, context):
    partner_ids = data['form']['partner_ids'][0][2]
    pool = pooler.get_pool(cr.dbname)
    user_ref = pool.get('res.users')
    survey_ref = pool.get('survey')
    group_id = pool.get('res.groups').search(cr, uid, [('name', '=', 'Survey / User')])
    act_id = pool.get('ir.actions.act_window')
    act_id = act_id.search(cr, uid, [('name', '=', 'Give Survey Response'), \
                                     ('res_model', '=' , 'survey.name.wiz'), ('view_type', '=', 'form')])
    out = "login,password\n"
    skipped = 0
    existing = ""
    created = ""
    error = ""
    res_user = ""
    user_exists = False
    attachments = []
    for id in survey_ref.browse(cr, uid, data['ids']):
        report = create_report(cr, uid, [id.id], 'report.survey.form', id.title)
        file = open(tools.config['addons_path'] + '/survey/report/' + id.title + ".pdf")
        file_data = ""
        while 1:
            line = file.readline()
            file_data += line
            if not line:
                break
        attachments.append((id.title + ".pdf", file_data))
        file.close()
        os.remove(tools.config['addons_path'] + '/survey/report/' + id.title + ".pdf")

    for partner in pool.get('res.partner').browse(cr, uid, partner_ids):
        for addr in partner.address:
            if not addr.email:
                skipped += 1
                continue
            user = user_ref.search(cr, uid, [('login', "=", addr.email)])
            if user:
                user = user_ref.browse(cr, uid, user[0])
                user_ref.write(cr, uid, user.id, {'survey_id':[[6, 0, data['ids']]]})
                mail = data['form']['mail'] % {'login':addr.email, 'passwd':user.password, \
                                            'name' : addr.name}
                if data['form']['send_mail_existing']:
                    tools.email_send(data['form']['mail_from'], [addr.email] , \
                                     data['form']['mail_subject_existing'] , mail)
                    existing += "- %s (Login: %s,  Password: %s)\n" % (user.name, addr.email, \
                                                                      user.password)
                continue
            user_id = user_ref.search(cr, uid, [('address_id', '=', addr.id)])
            if user_id:
                for user_email in user_ref.browse(cr, uid, user_id):
                    mail = data['form']['mail'] % {'login':user_email.login, \
                                                    'passwd':user_email.password, 'name' : addr.name}
                    if data['form']['send_mail_existing']:
                        tools.email_send(data['form']['mail_from'], [addr.email], \
                                              data['form']['mail_subject_existing'], mail)
                        res_user += "- %s (Login: %s,  Password: %s)\n" % \
                             (user_email.name, user_email.login, user_email.password)
                continue
            passwd = genpasswd()
            out += addr.email + ',' + passwd + '\n'
            mail = data['form']['mail'] % {'login' : addr.email, 'passwd' : passwd, 'name' : addr.name}
            if data['form']['send_mail']:

                ans = tools.email_send(data['form']['mail_from'], [addr.email], \
                                       data['form']['mail_subject'], mail, attach=attachments)

                if ans:
                    user = user_ref.create(cr, uid, {'name' : addr.name or 'Unknown',
                                        'login' : addr.email,
                                        'password' : passwd,
                                        'address_id' : addr.id,
                                        'groups_id' : [[6, 0, group_id]],
                                        'action_id' : act_id[0],
                                        'survey_id' :[[6, 0, data['ids']]]
                                       })
                    created += "- %s (Login: %s,  Password: %s)\n" % (addr.name or 'Unknown', \
                                                                      addr.email, passwd)
                else:
                    error += "- %s (Login: %s,  Password: %s)\n" % (addr.name or 'Unknown', \
                                                                    addr.email, passwd)
    note = ""
    if created:
        note += 'Created users:\n%s\n\n' % (created)
    if existing:
        note += 'Already existing users:\n%s\n\n' % (existing)
    if skipped:
        note += "%d contacts where ignored (an email address is missing).\n\n" % (skipped)
    if error:
        note += 'E-Mail not send successfully:\n====================\n%s\n' % (error)
    if res_user:
        note += 'E-mail ID used the following user:\n====================\n%s\n' % (res_user)
    return {'note': note}


def create_report(cr, uid, res_ids, report_name=False, file_name=False):
    if not report_name or not res_ids:
        return (False, Exception('Report name and Resources ids are required !!!'))
    try:
        ret_file_name = tools.config['addons_path'] + '/survey/report/' + file_name + '.pdf'
        service = netsvc.LocalService(report_name);
        (result, format) = service.create(cr, uid, res_ids, {}, {})
        fp = open(ret_file_name, 'wb+');
        fp.write(result);
        fp.close();
    except Exception, e:
        print 'Exception in create report:', e
        return (False, str(e))
    return (True, ret_file_name)

class send_mail_wizard(wizard.interface):
    states = {
        'init' : {
            'actions' : [check_survey],
            'result' : {'type' : 'form', 'arch' :_survey_form, 'fields' :_survey_fields, \
                             'state' : [('end', 'Cancel', 'gtk-cancel'), ('send', 'Send', 'gtk-go-forward')]}
                },
        'send' : {'actions' : [send_mail],
               'result' : {'type' : 'form',
                          'arch' : second_form,
                          'fields' : second_fields,
                          'state' : [('end', '_Ok')]}
               },
    }
send_mail_wizard('wizard.send.invitation')
