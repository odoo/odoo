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
import netsvc
import tools

sms_send_form = '''<?xml version="1.0"?>
<form string="%s">
    <separator string="%s" colspan="4"/>
    <field name="app_id"/>
    <newline/>
    <field name="user"/>
    <field name="password"/>
    <newline/>
    <field name="text" colspan="4"/>
</form>''' % ('SMS - Gateway: clickatell','Bulk SMS send')

sms_send_fields = {
    'app_id': {'string':'API ID', 'type':'char', 'required':True},
    'user': {'string':'Login', 'type':'char', 'required':True},
    'password': {'string':'Password', 'type':'char', 'required':True},
    'text': {'string':'SMS Message', 'type':'text', 'required':True}
}

def _sms_send(self, cr, uid, data, context):
    service = netsvc.LocalService("object_proxy")

    res_ids = service.execute(cr.dbname, uid, 'res.partner.address', 'search', [('partner_id','in',data['ids']),('type','=','default')])
    res = service.execute(cr.dbname, uid, 'res.partner.address', 'read', res_ids, ['mobile'])

    nbr = 0
    for r in res:
        to = r['mobile']
        if to:
            tools.sms_send(data['form']['user'], data['form']['password'], data['form']['app_id'], unicode(data['form']['text'], 'utf-8').encode('latin1'), to)
            nbr += 1
    return {'sms_sent': nbr}

class part_sms(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':sms_send_form, 'fields': sms_send_fields, 'state':[('end','Cancel'), ('send','Send SMS')]}
        },
        'send': {
            'actions': [_sms_send],
            'result': {'type': 'state', 'state':'end'}
        }
    }
part_sms('res.partner.sms_send')



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

