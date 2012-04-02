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

from osv import fields, osv
from tools.translate import _
import tools

class auction_lots_sms_send(osv.osv_memory):

    _name = "auction.lots.sms.send"
    _description = "Sms send "
    _columns= {
               'app_id':fields.char('API ID', size=64, required=True), 
               'user':fields.char('Login', size=64, required=True),
               'password':fields.char('Password', size=64, required=True),
               'text':fields.text('SMS Message', required=True)
    }
    
    def sms_send(self, cr, uid, ids, context=None):
        """
            to send sms
            
            @param cr: the current row, from the database cursor.
            @param uid: the current user’s ID for security checks.
            @param ids: the ID or list of IDs
            @param context: A standard dictionary 
            @return: number indicating the acknowledgement
        """
        if context is None: context = {}
        lot_obj = self.pool.get('auction.lots')
        partner_obj = self.pool.get('res.partner')
        for data in self.read(cr, uid, ids, context=context):
            lots = lot_obj.read(cr, uid, context.get('active_ids', []), ['obj_num','obj_price','ach_uid'])
            res = partner_obj.read(cr, uid, [l['ach_uid'][0] for l in lots if l['ach_uid']], ['gsm'], context)
            nbr = 0
            for r in res:
                add = partner_obj.address_get(cr, uid, [r['id']])['default']
                addr = partner_obj.browse(cr, uid, add, context=context)
                to = addr.mobile
                if to:
                    tools.sms_send(data['user'], data['password'], data['app_id'], unicode(data['text'], 'utf-8').encode('latin1'), to)
                    nbr += 1
            return {'sms_sent': nbr}
auction_lots_sms_send()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

