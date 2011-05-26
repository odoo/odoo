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

import logging
import random

from osv import osv, fields
from tools.misc import email_re, email_send
from tools.translate import _

from base.res.res_user import _lang_get



# welcome email sent to new portal users (note that calling tools.translate._
# has no effect except exporting those strings for translation)
WELCOME_EMAIL_SUBJECT = _("Your OpenERP account at %(company)s")
WELCOME_EMAIL_BODY = _("""Dear %(name)s,

You have been created an OpenERP account at %(url)s.

Your login account data is:
Database: %(db)s
User:     %(login)s
Password: %(password)s

--
OpenERP - Open Source Business Applications
http://www.openerp.com
""")

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



class wizard(osv.osv_memory):
    """
        A wizard to create portal users from instances of either 'res.partner'
        or 'res.partner.address'.  The purpose is to provide an OpenERP database
        access to customers or suppliers.
    """
    _name = 'res.portal.wizard'
    _description = 'Portal Wizard'
    
    _columns = {
        'portal_id': fields.many2one('res.portal', required=True,
            string='Portal',
            help="The portal in which new users must be added"),
        'user_ids': fields.one2many('res.portal.wizard.user', 'wizard_id',
            string='Users'),
    }
    _defaults = {
        'user_ids': (lambda self, *args: self._default_user_ids(*args))
    }

    def _default_user_ids(self, cr, uid, context):
        """ determine default user_ids from the active records """
        # determine relevant res.partner.address(es) depending on context
        addresses = []
        if context.get('active_model') == 'res.partner.address':
            address_obj = self.pool.get('res.partner.address')
            address_ids = context.get('active_ids', [])
            addresses = address_obj.browse(cr, uid, address_ids, context)
        elif context.get('active_model') == 'res.partner':
            partner_obj = self.pool.get('res.partner')
            partner_ids = context.get('active_ids', [])
            partners = partner_obj.browse(cr, uid, partner_ids, context)
            for p in partners:
                if p.address:
                    # take default address if present, or any address otherwise
                    def_addrs = filter(lambda a: a.type == 'default', p.address)
                    addresses.append(def_addrs[0] if def_addrs else p.address[0])
        
        # create user configs based on these addresses
        user_data = lambda address: {
                        'name': address.name,
                        'email': address.email,
                        'lang': address.partner_id and address.partner_id.lang,
                        'address_id': address.id,
                    }
        return map(user_data, addresses)

    def action_create(self, cr, uid, ids, context=None):
        """ create new users in portal(s), and notify them by email """
        # we copy the context to change the language for translating emails
        context0 = context or {}
        context = context0.copy()
        
        user = self.pool.get('res.users').browse(cr, ROOT_UID, uid, context0)
        if not user.user_email:
            raise osv.except_osv(_('Email required'),
                _('You must have an email address in your User Preferences'
                  ' to send emails.'))
        
        portal_obj = self.pool.get('res.portal')
        for wiz in self.browse(cr, uid, ids, context):
            # create new users in portal
            users_data = [ {
                    'name': u.name,
                    'login': u.email,
                    'password': random_password(),
                    'user_email': u.email,
                    'context_lang': u.lang,
                    'address_id': u.address_id.id,
                } for u in wiz.user_ids ]
            portal_obj.write(cr, ROOT_UID, [wiz.portal_id.id],
                {'users': [(0, 0, data) for data in users_data]}, context0)
            
            # send email to new users (translated in their language)
            for data in users_data:
                context['lang'] = data['context_lang']
                data['company'] = user.company_id.name
                data['db'] = cr.dbname
                data['url'] = wiz.portal_id.url or "(missing url)"
                
                email_from = user.user_email
                email_to = data['user_email']
                subject = _(WELCOME_EMAIL_SUBJECT) % data
                body = _(WELCOME_EMAIL_BODY) % data
                res = email_send(email_from, [email_to], subject, body)
                if not res:
                    logging.getLogger('res.portal.wizard').warning(
                        'Failed to send email from %s to %s', email_from, email_to)
        
        return {'type': 'ir.actions.act_window_close'}

wizard()



class wizard_user(osv.osv_memory):
    """
        A model to configure users in the portal wizard.
    """
    _name = 'res.portal.wizard.user'
    _description = 'Portal User Config'
    
    _columns = {
        'wizard_id': fields.many2one('res.portal.wizard', required=True,
            string='Wizard'),
        'name': fields.char(size=64, required=True,
            string='User Name',
            help="The user's real name"),
        'email': fields.char(size=64, required=True,
            string='E-mail',
            help="Will be used as user login.  "  
                 "Also necessary to send the account information to new users"),
        'lang': fields.selection(_lang_get, required=True,
            string='Language',
            help="The language for the user's user interface"),
        'address_id': fields.many2one('res.partner.address', required=True,
            string='Address'),
        'partner_id': fields.related('address_id', 'partner_id',
            type='many2one', relation='res.partner', readonly=True,
            string='Partner'),
    }

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

    _constraints = [
        (_check_email, 'Invalid email address', ['email']),
        (_check_exist, 'User login already exists', ['email']),
    ]

wizard_user()



