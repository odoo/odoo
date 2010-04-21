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
import re

email_send_form = '''<?xml version="1.0"?>
<form string="Mass Mailing">
    <field name="smtp_server" colspan="4"/>
    <newline/>
    <field name="subject" colspan="4"/>
    <newline/>
    <field name="text" colspan="4"/>
</form>'''

email_send_fields = {
    'smtp_server': {'string':"SMTP Server", 'type':'many2one', 'relation':'email.smtpclient', 'required':True},
    'subject': {'string':'Subject', 'type':'char', 'size':64, 'required':True},
    'text': {'string':'Message', 'type':'text_tag', 'required':True}
}

def merge_message(self, cr, uid, message, object, partner):
    
    def merge(match):
        exp = str(match.group()[2:-2]).strip()
        result = eval(exp, {'object':object, 'partner':partner})
        if result in (None, False):
            return str("--------")
        return str(result)
    
    com = re.compile('(\[\[.+?\]\])')
    msg = com.sub(merge, message)
    
    return msg

# this sends an email to ALL the addresses of the selected partners.
def _mass_mail_send(self, cr, uid, data, context):
    nbr = 0
    partners = pooler.get_pool(cr.dbname).get('res.partner').browse(cr, uid, data['ids'], context)
    email_server = pooler.get_pool(cr.dbname).get('email.smtpclient')
    
    for partner in partners:
        for adr in partner.address:
            if adr.email:
                name = adr.name or partner.name
                to = adr.email
                
                subject = merge_message(self, cr, uid, data['form']['subject'], adr, partner)
                message = merge_message(self, cr, uid, data['form']['text'], adr, partner)
                
                email_server.send_email(cr, uid, data['form']['smtp_server'], to, subject, message)
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
part_email('res.partner.spam_send.smtpclient')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: