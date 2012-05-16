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
from tools.misc import email_re
from tools.translate import _

from base.res.res_users import _lang_get



# welcome email sent to new portal users (note that calling tools.translate._
# has no effect except exporting those strings for translation)
WELCOME_EMAIL_SUBJECT = _("Your OpenERP account at %(company)s")
WELCOME_EMAIL_BODY = _("""Dear %(name)s,

You have been created an OpenERP account at %(url)s.

Your login account data is:
Database: %(db)s
User:     %(login)s
Password: %(password)s

%(message)s

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

def extract_email(user_email):
    """ extract the email address from a user-friendly email address """
    m = email_re.search(user_email or "")
    return m and m.group(0) or ""



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
        'message': fields.text(string='Invitation message',
            help="This text is included in the welcome email sent to the users"),
    }

    def _default_user_ids(self, cr, uid, context):
        """ determine default user_ids from the active records """
        def create_user_from_address(address):
            return {    # a user config based on a contact (address)
                'name': address.name,
                'user_email': extract_email(address.email),
                'lang': address.parent_id and address.parent_id.lang or 'en_US',
                'partner_id': address.parent_id and address.parent_id.id,
            }
        
        user_ids = []
        if context.get('active_model') == 'res.partner':
            partner_obj = self.pool.get('res.partner')
            partner_ids = context.get('active_ids', [])
            partners = partner_obj.browse(cr, uid, partner_ids, context)
            for p in partners:
                # add one user per contact, or one user if no contact
                if p.child_ids:
                    user_ids.extend(map(create_user_from_address, p.child_ids))
                else:
                    user_ids.append({'lang': p.lang or 'en_US', 'parent_id': p.id})
        
        return user_ids

    _defaults = {
        'user_ids': _default_user_ids
    }

    def action_create(self, cr, uid, ids, context=None):
        """ create new users in portal(s), and notify them by email """
        # we copy the context to change the language for translating emails
        context0 = context or {}
        context0['noshortcut'] = True           # prevent shortcut creation
        context = context0.copy()
        
        user_obj = self.pool.get('res.users')
        user = user_obj.browse(cr, ROOT_UID, uid, context0)
        if not user.user_email:
            raise osv.except_osv(_('Email required'),
                _('You must have an email address in your User Preferences'
                  ' to send emails.'))
        
        portal_obj = self.pool.get('res.portal')
        for wiz in self.browse(cr, uid, ids, context):
            # determine existing users
            login_cond = [('login', 'in', [u.user_email for u in wiz.user_ids])]
            existing_uids = user_obj.search(cr, ROOT_UID, login_cond)
            existing_users = user_obj.browse(cr, ROOT_UID, existing_uids)
            existing_logins = [u.login for u in existing_users]
            
            # create new users in portal (skip existing logins)
            new_users_data = [ {
                    'name': u.name,
                    'login': u.user_email,
                    'password': random_password(),
                    'user_email': u.user_email,
                    'context_lang': u.lang,
                    'share': True,
                    'action_id': wiz.portal_id.home_action_id and wiz.portal_id.home_action_id.id or False,
                    'partner_id': u.partner_id and u.partner_id.id,
                } for u in wiz.user_ids if u.user_email not in existing_logins ]
            portal_obj.write(cr, ROOT_UID, [wiz.portal_id.id],
                {'users': [(0, 0, data) for data in new_users_data]}, context0)
            
            # send email to all users (translated in their language)
            data = {
                'company': user.company_id.name,
                'message': wiz.message or "",
                'url': wiz.portal_id.url or _("(missing url)"),
                'db': cr.dbname,
            }
            mail_message_obj = self.pool.get('mail.message')
            dest_uids = user_obj.search(cr, ROOT_UID, login_cond)
            dest_users = user_obj.browse(cr, ROOT_UID, dest_uids)
            for dest_user in dest_users:
                context['lang'] = dest_user.context_lang
                data['login'] = dest_user.login
                data['password'] = dest_user.password
                data['name'] = dest_user.name
                
                email_from = user.user_email
                email_to = dest_user.user_email
                subject = _(WELCOME_EMAIL_SUBJECT) % data
                body = _(WELCOME_EMAIL_BODY) % data
                res = mail_message_obj.schedule_with_attach(cr, uid, email_from , [email_to], subject, body, context=context)
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
        'user_email': fields.char(size=64, required=True,
            string='E-mail',
            help="Will be used as user login.  "  
                 "Also necessary to send the account information to new users"),
        'lang': fields.selection(_lang_get, required=True,
            string='Language',
            help="The language for the user's user interface"),
        'partner_id': fields.many2one('res.partner',
            string='Partner'),
    }

    def _check_email(self, cr, uid, ids):
        """ check syntax of email address """
        for wuser in self.browse(cr, uid, ids):
            if not email_re.match(wuser.user_email): return False
        return True

    _constraints = [
        (_check_email, 'Invalid email address', ['email']),
    ]

wizard_user()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
