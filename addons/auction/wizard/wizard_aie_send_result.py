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

#
# Does not properly work concurently !!!
#

import wizard
import netsvc
from tools.translate import _

login_form = '''<?xml version="1.0"?>
<form title="Login">
    <field name="uname"></field>
    <newline/>
    <field name="password"></field>
</form>'''


send_form = '''<?xml version="1.0"?>
<form title="Selection">
    <field name="uname"></field>
    <field name="password"></field>
    <newline/>
    <field name="objects"></field>
    <newline/>
    <field name="dates" colspan="3"></field>
</form>'''

login_fields = {
    'uname': {'string':'Login', 'type':'char'},
    'password': {'string':'Password', 'type':'char'},
    'dates': {'string':'Auction Date', 'type':'selection', 'selection':[]}
}

send_fields = {
    'uname': {'string':'Login', 'type':'char', 'readonly':True},
    'password': {'string':'Password', 'type':'char', 'readonly':True},
    'objects': {'string':'# of objects', 'type':'integer', 'readonly':True},
    'dates': {'string':'Auction Date', 'type':'selection', 'selection':[]}
}

def _catalog_send(uname, passwd, did, catalog):
    def post_multipart(host, selector, fields, files):
        def encode_multipart_formdata(fields, files):
            BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
            CRLF = '\r\n'
            L = []
            for (key, value) in fields:
                L.append('--' + BOUNDARY)
                L.append('Content-Disposition: form-data; name="%s"' % key)
                L.append('')
                L.append(value)
            for (key,value) in files:
                L.append('--' + BOUNDARY)
                L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, key+'.pickle'))
                L.append('Content-Type: application/octet-stream')
                L.append('')
                L.append(value)
            L.append('--' + BOUNDARY + '--')
            L.append('')
            body = CRLF.join(L)
            content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
            return content_type, body
        content_type, body = encode_multipart_formdata(fields, files)
        import httplib

        headers = {"Content-type": content_type, "Accept": "*/*"}
        conn = httplib.HTTPConnection(host)
        conn.request("POST", '/bin/catalog_result.cgi', body, headers = headers)
        response = conn.getresponse()
        val = response.status
        conn.close()
        return val
    return post_multipart('auction-in-europe.com', "/bin/catalog_result.cgi", (('uname',uname),('password',passwd),('did',did)),(('file',catalog),))

def _get_dates(self,cr,uid, datas, context):
    global send_fields
    import httplib
    conn = httplib.HTTPConnection('www.auction-in-europe.com')
    conn.request("GET", "/aie_upload/dates_get_result.php?uname=%s&passwd=%s" % (datas['form']['uname'], datas['form']['password']))
    response = conn.getresponse()
    if response.status == 200:
        def _date_decode(x):
            return (x.split(' - ')[0], (' - '.join(x.split(' - ')[1:]).decode('latin1').encode('utf-8')))
        send_fields['dates']['selection'] = map(_date_decode, response.read().split('\n'))
    else:
        raise wizard.except_wizard(_('Error'),
                                   _("Connection to WWW.Auction-in-Europe.com failed !"))
    return {'objects':len(datas['ids'])}

def _send(self,cr,uid, datas, context):
    import pickle
    service = netsvc.LocalService("object_proxy")
    lots = service.execute(cr.dbname,uid, 'auction.lots', 'read', datas['ids'],  ['obj_num','obj_price'])
    args = pickle.dumps(lots)
    _catalog_send(datas['form']['uname'],datas['form']['password'], datas['form']['dates'], args)
    return {}

class wiz_auc_lots_pay(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':login_form, 'fields': login_fields, 'state':[('date_ask','Continue'),('end','Cancel')]}
        },
        'date_ask': {
            'actions': [_get_dates],
            'result': {'type': 'form', 'arch':send_form, 'fields': send_fields, 'state':[('send','Send on your website'),('end','Cancel')]}
        },
        'send': {
            'actions': [_send],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_auc_lots_pay('auction.lots.send.aie.results');


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

