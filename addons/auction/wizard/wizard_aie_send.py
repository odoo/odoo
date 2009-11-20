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

#
# Does not properly work concurently !!!
#
import pooler
import wizard
import netsvc
import base64
import mimetypes
import httplib
import threading
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
    <field name="lang"></field>
    <field name="numerotation"></field>
    <field name="img_send"></field>
    <newline/>
    <field name="dates" colspan="3"></field>
</form>'''

login_fields = {
    'uname': {'string':'Login', 'type':'char'},
    'password': {'string':'Password', 'type':'char'},
    'numerotation': {'string':'Numerotation', 'type':'selection', 'selection':[('prov','Provisoire'),('definite','Definitive (ordre catalogue)')]},
    'dates': {'string':'Auction Date', 'type':'selection', 'selection':[]}
}

send_fields = {
    'uname': {'string':'Login', 'type':'char', 'readonly':True},
    'password': {'string':'Password', 'type':'char', 'readonly':True},
    'objects': {'string':'# of objects', 'type':'integer', 'readonly':True},
    'lang': {'string':'Langage', 'type':'selection', 'selection':[('fr','fr'),('ned','ned'),('eng','eng'),('de','de')]},
    'numerotation': {'string':'Numerotation', 'type':'selection', 'selection':[('prov','Provisoire'),('definite','Definitive (ordre catalogue)')]},
    'dates': {'string':'Auction Date', 'type':'selection', 'selection':[]},
    'img_send': {'string':'Send Image also ?', 'type':'boolean'}
}

def _catalog_send(uname, passwd, lang, did, catalog):
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
        conn.request("POST", '/bin/catalog.cgi', body, headers = headers)
        response = conn.getresponse()
        val = response.status
        conn.close()
        return val
    return post_multipart('auction-in-europe.com', "/bin/catalog.cgi", (('uname',uname),('password',passwd),('did',did),('lang',lang)),(('file',catalog),))

def _photo_bin_send(uname, passwd, ref, did, photo_name, photo_data):
    def get_content_type(filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

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
            for (key, filename, data) in files:
                L.append('--' + BOUNDARY)
                L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
                L.append('Content-Type: %s' % get_content_type(filename))
                L.append('')
                L.append(data)
            L.append('--' + BOUNDARY + '--')
            L.append('')
            body = CRLF.join(L)
            content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
            return content_type, body
        content_type, body = encode_multipart_formdata(fields, files)

        headers = {"Content-type": content_type, "Accept": "*/*"}
        conn = httplib.HTTPConnection(host)
        conn.request("POST", '/bin/photo.cgi', body, headers = headers)
        response = conn.getresponse()
        val = response.status
        conn.close()
        return val
    return post_multipart('auction-in-europe.com', "/bin/photo.cgi", (('uname',uname),('ref',ref),('passwd',passwd),('did',did)),(('file',photo_name,photo_data),))


def _photos_send(cr,uid, uname, passwd, did, ids):
    for (ref,id) in ids:
        service = netsvc.LocalService("object_proxy")
#       ids_attach = service.execute(db_name,uid, 'ir.attachment', 'search', [('res_model','=','auction.lots'), ('res_id', '=',id)])
        datas = service.execute(cr.db_name,uid, 'auction.lots', 'read',[id], ['name','image'])
        if len(datas):
            bin = base64.decodestring(datas[0]['image'])
            fname = datas[0]['name']
            _photo_bin_send(uname, passwd, ref, did, fname, bin)

def _get_dates(self,cr,uid, datas,context={}):
    global send_fields
    import httplib
    conn = httplib.HTTPConnection('www.auction-in-europe.com')
    conn.request("GET", "/aie_upload/dates_get.php?uname=%s&passwd=%s" % (datas['form']['uname'], datas['form']['password']))
    response = conn.getresponse()
    if response.status == 200:
        def _date_decode(x):
            return (x.split(' - ')[0], (' - '.join(x.split(' - ')[1:]).decode('latin1','replace').encode('utf-8','replace')))
        send_fields['dates']['selection'] = map(_date_decode, response.read().split('\n'))
    else:
        raise wizard.except_wizard(_('Error'), _("Connection to WWW.Auction-in-Europe.com failed !"))
    return {'objects':len(datas['ids'])}

def _send(self,db_name,uid, datas,context={}):
    import pickle, thread, sql_db
    #cr = pooler.get_db(cr.dbname).cursor()

#   cr=sql_db.db.cursor()
    cr = pooler.get_db(db_name).cursor()

    cr.execute('select name,aie_categ from auction_lot_category')
    vals = dict(cr.fetchall())
    cr.close()

    service = netsvc.LocalService("object_proxy")
    lots = service.execute(cr.dbname,uid, 'auction.lots', 'read', datas['ids'],  ['obj_num','lot_num','obj_desc','bord_vnd_id','lot_est1','lot_est2','artist_id','lot_type','aie_categ'])
    ids = []
    for l in lots:
        if datas['form']['numerotation']=='prov':
            l['ref']='%s%03d' % (l['bord_vnd_id'][1],l['lot_num'])
            l['ref2']='%s%03d' % (l['bord_vnd_id'][1],l['lot_num'])
        else:
            l['ref']='%04d' % (l['obj_num'],)
            l['ref2']='%s%03d' % (l['bord_vnd_id'][1],l['lot_num'])
        if l['artist_id']:
            l['artist_id'] = l['artist_id'][1]
        else:
            l['artist_id'] = ''
        for n in ('obj_desc','artist_id','lot_type'):
            try:
                l[n]=l[n].decode('utf-8','replace').encode('latin1','replace')
            except:
                l[n]=''
        del l['lot_num']
        del l['obj_num']
        del l['bord_vnd_id']
        l['aie_categ'] = vals.get(l['lot_type'], False)
        ids.append((l['ref'], l['id']))
    args = pickle.dumps(lots)
    thread.start_new_thread(_catalog_send, (datas['form']['uname'],datas['form']['password'],datas['form']['lang'],datas['form']['dates'], args))
    if(datas['form']['img_send']==True):
        thread.start_new_thread(_photos_send, (cr.dbname,uid, datas['form']['uname'],datas['form']['password'],datas['form']['dates'], ids))
    return {}

def _send_pdf(self, cr, uid, data, context):
    threaded_calculation = threading.Thread(target=_send, args=(self, cr.dbname, uid, data, context))
    threaded_calculation.start()
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
            'actions': [_send_pdf],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_auc_lots_pay('auction.lots.send.aie');


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

