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

import logging
import random

from osv import osv, fields
from tools.misc import email_re, email_send
from tools.translate import _

from base.res.res_user import _lang_get



ROOT_UID = 1

# character sets for passwords, excluding 0, O, o, 1, I, l
_PASSU = 'ABCDEFGHIJKLMNPQRSTUVWXYZ'
_PASSL = 'abcdefghijkmnpqrstuvwxyz'
_PASSD = '23456789'

def random_password():
    # get 3 uppercase letters, 3 lowercase letters, 2 digits, and shuffle them
    chars = map(random.choice, [_PASSU] * 3 + [_PASSL] * 3 + [_PASSD] * 2)
    random.shuffle(chars)
    return ''.join(chars)



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
    
    _constraints = [
        (lambda self,*args: self._check_email(*args), 'Invalid email address', ['email']),
        (lambda self,*args: self._check_exist(*args), 'User login already exists', ['email']),
    ]

    def default_get(self, cr, uid, fields, context=None):
        """ determine default name, email, address_id and lang from the active
            record """
        # get existing defaults
        defs = super(user_wizard, self).default_get(cr, uid, fields, context)
        
        # determine a res.partner.address depending on current context
        address = None
        if context.get('active_model') == 'res.partner.address':
            address_obj = self.pool.get('res.partner.address')
            address = address_obj.browse(cr, uid, context.get('active_id'), context)
        
        elif context.get('active_model') == 'res.partner':
            partner_obj = self.pool.get('res.partner')
            partner = partner_obj.browse(cr, uid, context.get('active_id'), context)
            if partner and partner.address:
                # take default address if present, or any address otherwise
                addresses = filter(lambda a: a.type == 'default', partner.address)
                address = addresses[0] if addresses else partner.address[0]
        
        # override name, email, address_id, and lang
        if address:
            defs['name'] = address.name
            defs['email'] = address.email
            defs['address_id'] = address.id
            defs['lang'] = address.partner_id and address.partner_id.lang
        
        return defs

    def _check_email(self, cr, uid, ids):
        """ check syntax of email address """
        for wizard in self.browse(cr, uid, ids):
            if not email_re.match(wizard.email): return False
        return True

    def _check_exist(self, cr, uid, ids):
        """ check whether login (email) already in use """
        user_obj = self.pool.get('res.users')
        for wizard in self.browse(cr, uid, ids):
            condition = [('login', '=', wizard.email)]
            if user_obj.search(cr, ROOT_UID, condition): return False
        return True

    def do_create(self, cr, uid, ids, context=None):
        """ create a new user in the portal, and notify them by email """
        # we copy the context to change the language for translating emails
        context0 = context or {}
        context = context0.copy()
        
        user = self.pool.get('res.users').browse(cr, ROOT_UID, uid, context0)
        if not user.user_email:
            raise osv.except_osv(_('Email required'),
                _('You must have an email address in your User Preferences'
                  ' to send emails.'))
        
        portal_obj = self.pool.get('res.portal')
        for wizard in self.browse(cr, uid, ids, context):
            # add a new user in wizard.portal_id
            user_values = {
                'name': wizard.name,
                'login': wizard.email,
                'password': random_password(),
                'user_email': wizard.email,
                'address_id': wizard.address_id.id,
                'context_lang': wizard.lang,
            }
            values = {'users': [(0, 0, user_values)]}
            portal_obj.write(cr, ROOT_UID, [wizard.portal_id.id], values, context0)
            
            # send email to new user (translated in language of new user)
            context['lang'] = user_values['context_lang']
            user_values['dbname'] = cr.dbname
            user_values['url'] = "(missing url)"
            
            email_to = user_values['user_email']
            subject = _("Your OpenERP account at %s") % user.company_id.name
            body = _(
                "Dear %(name)s,\n\n"
                "You have been created an OpenERP account at %(url)s.\n\n"
                "Your login account data is:\n"
                "Database: %(dbname)s\n"
                "User:     %(login)s\n"
                "Password: %(password)s\n\n"
                "--\n"
                "OpenERP - Open Source Business Applications\n"
                "http://www.openerp.com\n"
                ) % user_values
            res = email_send(user.user_email, [email_to], subject, body)
            if not res:
                logging.getLogger('res.portal.user_wizard').warning(
                    'Failed to send email from %s to %s', user.user_email, email_to)

        return {}

user_wizard()



