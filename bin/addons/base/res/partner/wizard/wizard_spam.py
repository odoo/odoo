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

import wizard
import pooler
import tools

email_send_form = '''<?xml version="1.0"?>
<form string="Mass Mailing">
    <field name="from"/>
    <newline/>
    <field name="subject"/>
    <newline/>
    <field name="text"/>
</form>'''

email_send_fields = {
    'from': {'string':"Sender's email", 'type':'char', 'size':64, 'required':True},
    'subject': {'string':'Subject', 'type':'char', 'size':64, 'required':True},
    'text': {'string':'Message', 'type':'text_tag', 'required':True}
}

# this sends an email to ALL the addresses of the selected partners.
def _mass_mail_send(self, cr, uid, data, context):
    nbr = 0
    partners = pooler.get_pool(cr.dbname).get('res.partner').browse(cr, uid, data['ids'], context)
    for partner in partners:
        for adr in partner.address:
            if adr.email:
                name = adr.name or partner.name
                to = '%s <%s>' % (name, adr.email)
#TODO: add some tests to check for invalid email addresses
#CHECKME: maybe we should use res.partner/email_send
                tools.email_send(data['form']['from'], [to], data['form']['subject'], data['form']['text'],subtype='html')
                nbr += 1
        pooler.get_pool(cr.dbname).get('res.partner.event').create(cr, uid,
                {'name': 'Email sent through mass mailing',
                 'partner_id': partner.id,
                 'description': data['form']['text'], })
#TODO: log number of message sent
    return {'email_sent': nbr}

class part_email(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': email_send_form, 'fields': email_send_fields, 'state':[('end','Cancel'), ('send','Send Email')]}
        },
        'send': {
            'actions': [_mass_mail_send],
            'result': {'type': 'state', 'state':'end'}
        }
    }
part_email('res.partner.spam_send')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

