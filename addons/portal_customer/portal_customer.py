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
    
    def onchange_portal_create_user(self, cr, uid, ids, field, context=None):
        res_users_obj = self.pool.get('res.users')
        if field == 1:
            name = self.browse(cr, uid, ids, context=context)[0].name
            login = self.browse(cr, uid, ids, context=context)[0].email
            res_users_obj.create(cr, uid, {'name':name, 'login':login, 'new_password':login}, context=context)
        return True
    
res_partner()