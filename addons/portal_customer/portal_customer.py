# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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
import time

class res_partner(osv.osv):
    
    _inherit = 'res.partner'
    _columns = {
            'customer_portal_access': fields.boolean('Portal'),
        }
    
    def mail_user_confirm(self, cr, uid, ids, context=None):
        """
        Send email to user when the event is confirmed
        """
        email_template_obj = self.pool.get('email.template')
        portal_user_id = self.browse(cr, uid, ids, context=context)[0].id
        template_id = email_template_obj.search(cr, uid, [('name','=','Customer Portal User Confirmation')], context=context)[0]
        if template_id:
            mail_message = email_template_obj.send_mail(cr,uid,template_id,portal_user_id)
        return True
    
    def onchange_portal_create_user(self, cr, uid, ids, customer_portal_access, context=None):
        res_users_obj = self.pool.get('res.users')
        self.mail_user_confirm(cr, uid, ids)
        if customer_portal_access:
            name = self.browse(cr, uid, ids, context=context)[0].name
            login = self.browse(cr, uid, ids, context=context)[0].email
            res_users_obj.create(cr, uid, {'name':name, 'login':login, 'new_password':login}, context=context)
        return {}
    
res_partner()