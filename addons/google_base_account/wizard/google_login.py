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

from osv import fields,osv
from tools.translate import _
try:
    import gdata.contacts.service
    import gdata.contacts.client
    import gdata.calendar.service
except ImportError:
    raise osv.except_osv(_('Google Contacts Import Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))

class google_login(osv.osv_memory):
    _description ='Google Contact'
    _name = 'google.login'
    _columns = {
        'user': fields.char('Google Username', size=64, required=True),
        'password': fields.char('Google Password', size=64),
    }

    def google_login(self, user, password, type='', context=None):
        if type == 'group':
            gd_client = gdata.contacts.client.ContactsClient(source='OpenERP')
        if type == 'contact':
            gd_client = gdata.contacts.service.ContactsService()
        if type == 'calendar':
            gd_client = gdata.calendar.service.CalendarService()
        if type =='docs_client':
            gd_client = gdata.docs.client.DocsClient()
        else:
            gd_client = gdata.contacts.service.ContactsService()
        try:
            gd_client.ClientLogin(user, password, gd_client.source)
        except Exception:
            return False
        return gd_client


    def default_get(self, cr, uid, fields, context=None):
        res = super(google_login, self).default_get(cr, uid, fields, context=context)
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        if 'user' in fields:
            res.update({'user': user_obj.gmail_user})
        if 'password' in fields:
            res.update({'password': user_obj.gmail_password})
        return res

    def login(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids)[0]
        user = data['user']
        password = data['password']
        if self.google_login(user, password):
            res = {
                   'gmail_user': user,
                   'gmail_password': password
            }
            self.pool.get('res.users').write(cr, uid, uid, res, context=context)
        else:
            raise osv.except_osv(_('Error'), _("Authentication failed check the user and password !"))

        return self._get_next_action(cr, uid, context=context)

    def _get_next_action(self, cr, uid, context=None):
        return {'type': 'ir.actions.act_window_close'}

google_login()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
