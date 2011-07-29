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

import netsvc
from tools.translate import _
from osv import fields, osv

class auction_lots_pay(osv.osv_memory):
    _name = 'auction.lots.send.aie.results'
    _description = 'Send results to Auction-in-europe.com'
    
    
    def _date_get(self, cr, uid, context=None):
        selection = context and context.get('selection')
        if selection:
            return [('','')] + selection
        return [('','')]
    
    _columns = {
        'uname': fields.char('Login', size=64),
        'password': fields.char('Password', size=64),
        'objects': fields.integer('# of objects'),
        'dates': fields.selection(_date_get,'Auction Date'),
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
        res = super(auction_lots_pay, self).default_get(cr, uid, fields, context=context)
        if 'uname' in fields and context.get('uname',False):
            res['uname'] = context.get('uname')
        if 'password' in fields and context.get('password',False):
            res['password'] = context.get('password')
        return res

    def _catalog_send(self, uname, passwd, did, catalog):
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
    
    def get_dates(self, cr, uid, ids, context=None):
        if context is None: 
            context = {}
        import httplib
        conn = httplib.HTTPConnection('www.auction-in-europe.com')
        data_obj = self.pool.get('ir.model.data')
        datas = self.read(cr, uid, ids[0],['uname','password'])
        conn.request("GET", "/aie_upload/dates_get_result.php?uname=%s&passwd=%s" % (datas['uname'], datas['password']))
        response = conn.getresponse()
        if response.status == 200:
            def _date_decode(x):
                return (x.split(' - ')[0], (' - '.join(x.split(' - ')[1:]).decode('latin1').encode('utf-8')))
            context['selection'] = map(_date_decode, response.read().split('\n'))
            self._date_get(cr, uid, context=context)
        else:
            raise osv.except_osv(_('Error'),
                                       _("Connection to WWW.Auction-in-Europe.com failed !"))
        id1 = data_obj._get_id(cr, uid, 'auction', 'view_auction_lots_send_result_send')
        res_id = data_obj.browse(cr, uid, id1, context=context).res_id
        context.update(datas)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'auction.lots.send.aie.results',
            'views': [(res_id,'form')],
            'type': 'ir.actions.act_window',
            'target':'new',
            'context': context
        }
    
    def send(self, cr, uid, ids, context=None):
        if context is None: 
            context = {}
        import pickle
        datas = self.read(cr, uid, ids[0],['uname','password','dates'])
        lots = self.pool.get('auction.lots').read(cr, uid, context['active_ids'],  ['obj_num','obj_price'])
        args = pickle.dumps(lots)
        self._catalog_send(datas['uname'], datas['password'], datas['dates'], args)
        return {'type': 'ir.actions.act_window_close'}
    
auction_lots_pay()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

