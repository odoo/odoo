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

from osv import fields,osv,orm
from tools.translate import _
import gdata.contacts.service

class google_login(osv.osv_memory):
    _description ='Google Contact'
    _name = 'google.login'
    _columns = {
        'user': fields.char('User Name', size=64, required=True),
        'password': fields.char('Password', size=64),
    }
    def google_login(self,cr,uid,user,password,context=None):
        gd_client = gdata.contacts.service.ContactsService()
        gd_client.email = user
        gd_client.password = password
        gd_client.source = 'OpenERP'    
        try:
            gd_client.ProgrammaticLogin()     
        except Exception, e:
           return False
        return gd_client
        
    def check_login(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        user = data['user']
        password = data['password']
        gd_client = gdata.contacts.service.ContactsService()
        gd_client.email = user
        gd_client.password = password
        gd_client.source = 'OpenERP'
        try:
            gd_client.ProgrammaticLogin()     
            res = {
                   'gmail_user': user,
                   'gmail_password': password
            }
            self.pool.get('res.users').write(cr, uid, uid, res, context=context)            
        except Exception, e:
            raise osv.except_osv(_('Error!'),_('%s' % (e))) 
        
        return gd_client
google_login()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
