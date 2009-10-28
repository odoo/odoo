# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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


import time
import wizard
import osv
import pooler

cc_form = '''<?xml version="1.0"?>
<form string="Add a CC">
    <field name="send_to"/>
    <newline/>
    <field name="user_id" attrs="{'readonly' : [('send_to','!=','user')], 'required' : [('send_to','=','user')]}"/>
    <field name="partner_id" attrs="{'readonly' : [('send_to','!=','partner')], 'required' : [('send_to','=','partner')]}"/>/>
    <field name="email"/>
</form>'''

#on_change="change_email(user_id, partner_id)" 

cc_fields = {
    'send_to' : {'string' : 'Send to', 'type' : 'selection', 'required' :True, \
                      'selection' :[('user','User'),('partner','Partner'),('email','Email Address')], \
                      'default' : 'email'},
    'user_id' : {'string' : 'User', 'type' : 'many2one', 'relation' : 'res.users'},
    'partner_id' : {'string' : 'Partner', 'type' : 'many2one', 'relation' : 'res.partner'},
    'email' : {'string' : 'Email', 'type' : 'char', 'size' : 24},
}

#def change_email(self, cr, uid, data, context):
#    return {}

def email_cc_add(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    history_line = pool.get('crm.case.history').browse(cr, uid, data['id'])
    crm_case = pool.get('crm.case')
    case_id = history_line.log_id.case_id.id
    crm_case.write(cr, uid, case_id, {'email_cc' : data['form']['email']})
    #TODO: send the latest email to the email adderss
    return {}


class wizard_add_cc(wizard.interface):
    states = {
        'init' : {
            'actions' : [], 
            'result' : {'type' : 'form', 'arch' : cc_form, 'fields' :cc_fields,\
                         'state' :[('end','Cancel', 'gtk-cancel'),('add','Ok', 'gtk-go-forward' )]}
        },
        'add' : {
            'actions' : [email_cc_add],
            'result' : {'type' : 'state', 'state' : 'end'}
        }
    }
wizard_add_cc('crm.case.email.add_cc')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

