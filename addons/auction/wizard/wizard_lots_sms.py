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

import wizard
import netsvc

import urllib

sms_send_form = '''<?xml version="1.0"?>
<form title="%s">
    <separator string="%s" colspan="4"/>
    <field name="app_id"/>
    <newline/>
    <field name="user"/>
    <field name="password"/>
    <newline/>
    <field name="text" colspan="3"/>
</form>''' % ('SMS - Gateway: clickatell', 'Bulk SMS send')

sms_send_fields = {
    'app_id': {'string':'API ID', 'type':'char', 'required':True},
    'user': {'string':'Login', 'type':'char', 'required':True},
    'password': {'string':'Password', 'type':'char', 'required':True},
    'text': {'string':'SMS Message', 'type':'text', 'required':True, 'value':'Les lots [lots] vous ont etes adjuges. -- Rops'}
}
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import wizard
import netsvc
import pooler

sms_send_form = '''<?xml version="1.0"?>
<form string="%s">
    <separator string="%s" colspan="4"/>
    <field name="app_id"/>
    <newline/>
    <field name="user"/>
    <field name="password"/>
    <newline/>
    <field name="text" colspan="3"/>
</form>''' % ('SMS - Gateway: clickatell','Bulk SMS send')

sms_send_fields = {
    'app_id': {'string':'API ID', 'type':'char', 'required':True},
    'user': {'string':'Login', 'type':'char', 'required':True},
    'password': {'string':'Password', 'type':'char', 'required':True},
    'text': {'string':'SMS Message', 'type':'text', 'required':True}
}

def _sms_send(self, cr, uid, data, context):
    service = netsvc.LocalService("object_proxy")
    lots = service.execute(cr.dbname,uid, 'auction.lots', 'read', data['ids'], ['obj_num','obj_price','ach_uid'])
    res = service.execute(cr.dbname,uid, 'res.partner', 'read', [l['ach_uid'] for l in lots if l['ach_uid']], ['gsm'])
    #res = service.execute(cr.dbname, uid, 'res.partner', 'read', data['ids'], ['gsm'])
#   service = netsvc.LocalService("object_proxy")
#   pool=pooler.get_pool(cr.dbname)
#   lots=pool.get('auction.lots').browse(cr,uid,data['id'],context)
#   r=lots.ach_uid.id
    nbr = 0
    for r in res:
        to = r['mobile']
        if to:
            tools.smssend(data['form']['user'], data['form']['password'], data['form']['app_id'], unicode(data['form']['text'], 'utf-8').encode('latin1'), to)
            nbr += 1
    return {'sms_sent': nbr}

    if to:
        tools.smssend(data['form']['user'], data['form']['password'], data['form']['app_id'], unicode(data['form']['text'], 'utf-8').encode('latin1'), to)
        nbr += 1
    return {'sms_sent': nbr}
#
#def _sms_send(self, uid, datas):
#   service = netsvc.LocalService("object_proxy")
#   pool=pooler.ger_pool(cr.dbname)
#   lots=pool.get('auction.lots').browse(cr,uid,datas['ids'],context)
#   #lots = service.execute(uid, 'auction.lots', 'read', datas['ids'], ['obj_num','obj_price','ach_uid'])
#   #part = service.execute(uid, 'res.partner', 'read', [l['ach_uid'] for l in lots if l['ach_uid']], ['gsm'])
#   
#   part =ach_uid.id
#   part = map(lambda x: (x.id,x.mobile), part)
#   for l in lots:
#       part.append(str(l.obj_num)+'-%dEUR' % int(l.obj_price))
#
#   for p in part.values():
#       to = p.mobile
#       if to:
#           params = urllib.urlencode({'user': datas['form']['user'], 'password': datas['form']['password'], 'api_id': datas['form']['app_id'], 'text':unicode(datas['form']['text'].replace('[lots]',', '.join(p['lots'])), 'utf-8').encode('latin1'), 'to':to})
#           f = urllib.urlopen("http://196.7.150.220/http/sendmsg", params)
#           nbr+=1
#   return {'sms_sent':nbr}

class lots_sms(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':sms_send_form, 'fields': sms_send_fields, 'state':[('send','Send SMS'), ('end','Cancel')]}
        },
        'send': {
            'actions': [_sms_send],
            'result': {'type': 'state', 'state':'end'}
        }
    }
lots_sms('auction.lots.sms_send');

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

