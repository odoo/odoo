# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
from tools.translate import _
from base.res.res_user import _lang_get



class user_wizard(osv.osv_memory):
    """
        A wizard to create a portal user from a res.partner.address.  The use
        case of the wizard is to provide access to a customer or supplier.
    """
    _name = 'res.portal.user_wizard'
    _description = 'Portal User Wizard'
    
    _columns = {
        'name': fields.char(size=64, required=True,
            string='User Name',
            help="The new user's real name"),
        'login': fields.char(size=64, required=True,
            string='Login',
            help="Used to log into the system"),
        'email': fields.char(size=64, required=True,
            string='E-mail',
            help="A welcome e-mail will be sent to the new user, "
                 "with the necessary information to connect to OpenERP"),
        'lang': fields.selection(_lang_get, required=True,
            string='Language',
            help="The language for the user's user interface"),
        'address_id': fields.many2one('res.partner.address', readonly=True,
            string='Address'),
        'portal_id': fields.many2one('res.portal', required=True,
            string='Portal',
            help="The Portal that the new user must belong to"),
    }
    
    def default_get(self, cr, uid, fields, context=None):
        """ define the default name, login, email, address_id from the active
            res.partner.address record """
        # get existing defaults
        defs = super(user_wizard, self).default_get(cr, uid, fields, context)
        
        # override name, login, email, address_id, and lang
        if context and ('active_id' in context):
            address_obj = self.pool.get('res.partner.address')
            address = address_obj.browse(cr, uid, context['active_id'], context)
            defs['name'] = address.name
            defs['login'] = address.email
            defs['email'] = address.email
            defs['address_id'] = address.id
            if address.partner_id and address.partner_id.lang:
                defs['lang'] = address.partner_id.lang
        
        return defs

    def onchange_email(self, cr, uid, ids, email):
        """ assign email on login """
        return {'value': {'login': email}}

user_wizard()



