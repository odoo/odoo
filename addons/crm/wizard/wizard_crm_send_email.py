# -*- coding: utf-8 -*-
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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
import tools
from tools.translate import _


email_send_form = '''<?xml version="1.0"?>
<form string="Mass Mailing">
    <field name="to"/>
    <newline/>
    <field name="cc"/>
    <newline/>
    <field name="subject"/>
    <newline/>
    <field name="text" />
</form>'''

email_send_fields = {
    'to': {'string':"To", 'type':'char', 'size':64, 'required':True},
    'cc': {'string':"CC", 'type':'char', 'size':128,},
    'subject': {'string':'Subject', 'type':'char', 'size':128, 'required':True},
    'text': {'string':'Message', 'type':'text_tag', 'required':True}
}

# this sends an email to ALL the addresses of the selected partners.
def _mass_mail_send(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    case_pool=pool.get('crm.case')

    hist_obj = pool.get('crm.case.history').browse(cr,uid,data['ids'])[0]
    case = hist_obj.log_id.case_id
    case_pool._history(cr, uid, [case], _('Send'), history=True, email=False)
    case_pool.write(cr, uid, [case.id], {
                'som': False,
                'canal_id': False,
                })
    emails = [data['form']['to']] + (data['form']['cc'] or '').split(',')
    emails = filter(None, emails)
    body = data['form']['text']
    if case.user_id.signature:
        body += '\n\n%s' % (case.user_id.signature)
    tools.email_send(
        case.user_id.address_id.email,
        emails,
        data['form']['subject'],
        case_pool.format_body(body),
        reply_to=case.section_id.reply_to,
        tinycrm=str(case.id)
    )
    return {}

def _get_info(self, cr, uid, data, context):
    if not data['id']:
        raise wizard.except_wizard(_('Error'),_('There is no mail to reply!'))
    pool = pooler.get_pool(cr.dbname)
    hist_obj = pool.get('crm.case.history').browse(cr,uid,data['ids'])[0]
    case = hist_obj.log_id.case_id
    if not case.email_from:
        raise wizard.except_wizard(_('Error'),_('You must put a Partner eMail to use this action!'))
    if not case.user_id:
        raise wizard.except_wizard(_('Error'),_('You must define a responsible user for this case in order to use this action!'))
    return {'to': case.email_from,'subject': '['+str(case.id)+'] '+case.name,'cc': case.email_cc or '', 'text': '> ' + hist_obj.description.replace('\n','\n> ')}
    
class wizard_send_mail(wizard.interface):
    states = {
        'init': {
            'actions': [_get_info],
            'result': {'type': 'form', 'arch': email_send_form, 'fields': email_send_fields, 'state':[('end','Cancel','gtk-cancel'), ('send','Send Email','gtk-go-forward')]}
        },
        'send': {
            'actions': [_mass_mail_send],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wizard_send_mail('crm.send.mail')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

