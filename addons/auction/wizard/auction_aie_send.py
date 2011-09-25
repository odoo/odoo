# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
# Does not properly work concurrently !!!
#
from osv import fields,osv
from tools.translate import _
import base64
import httplib
import mimetypes
import netsvc
import threading

class auction_lots_send_aie(osv.osv_memory):
    _name = 'auction.lots.send.aie'
    _descritption = 'Send to website'
    
    def _date_get(self, cr, uid, context=None):
        selection = context and context.get('selection')
        if selection:
            return [('','')] + selection
        return [('','')]

    _columns = {
        'uname': fields.char('Login', size=64),
        'password': fields.char('Password', size=64),
        'objects': fields.integer('# of objects', readonly=True),
        'lang': fields.selection([('fr','fr'),('ned','ned'),('eng','eng'),('de','de')],'Language'),
        'numerotation': fields.selection([('prov','Provisoire'),('definite','Definitive (ordre catalogue)')],'Numerotation'),
        'dates': fields.selection(_date_get,'Auction Date'),
        'img_send': fields.boolean('Send Image also ?'),   
    }
    
    def default_get(self, cr, uid, fields, context=None):
        """ 
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """
        if context is None: 
            context = {}
        res = super(auction_lots_send_aie, self).default_get(cr, uid, fields, context=context)
        if 'uname' in fields and context.get('uname',False):
            res['uname'] = context.get('uname')
        if 'password' in fields and context.get('password',False):
            res['password'] = context.get('password')
        return res
    
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
    
    
    def _photos_send(cr, uid, uname, passwd, did, ids):
        for (ref,id) in ids:
            datas = self.pool.get('auction.lots').read(cr, uid, [id], ['name','image'])
            if len(datas):
                bin = base64.decodestring(datas[0]['image'])
                fname = datas[0]['name']
                self._photo_bin_send(uname, passwd, ref, did, fname, bin)
    
    def get_dates(self, cr, uid, ids, context=None):
        if context is None: 
            context = {}
        import httplib
        data_obj = self.pool.get('ir.model.data')
        conn = httplib.HTTPConnection('www.auction-in-europe.com')
        datas = self.read(cr, uid, ids[0],['uname','password'])
        conn.request("GET", "/aie_upload/dates_get.php?uname=%s&passwd=%s" % (datas['uname'], datas['password']))
        response = conn.getresponse()
        if response.status == 200:
            def _date_decode(x):
                return (x.split(' - ')[0], (' - '.join(x.split(' - ')[1:]).decode('latin1','replace').encode('utf-8','replace')))
            context['selection'] = map(_date_decode, response.read().split('\n'))
            self._date_get(cr, uid, context=context)
        else:
            raise osv.except_osv(_('Error'), _("Connection to WWW.Auction-in-Europe.com failed !"))
        id1 = data_obj._get_id(cr, uid, 'auction', 'view_auction_lots_send')
        res_id = data_obj.browse(cr, uid, id1, context=context).res_id
        context.update(datas)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'auction.lots.send.aie',
            'views': [(res_id,'form')],
            'type': 'ir.actions.act_window',
            'target':'new',
            'context': context
        }
    
    def _send(self, cr, uid, ids, context=None):
        import pickle, thread, sql_db
        cr.execute('select name,aie_categ from auction_lot_category')
        vals = dict(cr.fetchall())
        cr.close()
        if context is None: 
            context = {}
    
        lots = self.pool.get('auction.lots').read(cr, uid, context.get('active_ids',[]), ['obj_num','lot_num','obj_desc','bord_vnd_id','lot_est1','lot_est2','artist_id','lot_type','aie_categ'])
        lots_ids = []
        datas = self.read(cr, uid, ids[0],['uname','login','lang','numerotation','dates'])
        for l in lots:
            if datas['numerotation']=='prov':
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
            lots_ids.append((l['ref'], l['id']))
        args = pickle.dumps(lots)
        thread.start_new_thread(_catalog_send, (datas['uname'],datas['password'],datas['lang'],datas['dates'], args))
        if(datas['form']['img_send']==True):
            thread.start_new_thread(_photos_send, (cr.dbname, uid, datas['uname'], datas['password'],datas['dates'], lots_ids))
        return {}
    
    def send_pdf(self, cr, uid, ids, context=None):
        threaded_calculation = threading.Thread(target=self._send, args=(cr, uid, ids, context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}

auction_lots_send_aie()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

