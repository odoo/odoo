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
from tools.translate import _
from tools.misc import email_re

from base.res.res_users import _lang_get
_logger = logging.getLogger(__name__)



def extract_email(user_email):
    """ extract the email address from a user-friendly email address """
    m = email_re.search(user_email or "")
    return m and m.group(0) or ""


# welcome email sent to new portal users (note that calling tools.translate._
# has no effect except exporting those strings for translation)
WELCOME_EMAIL_SUBJECT = _("Your OpenERP account at %(company)s")
WELCOME_EMAIL_BODY = _("""Dear %(name)s,

You have been created an OpenERP account of %(portal)s at %(url)s.

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




class wizard(osv.osv_memory):
    """
        A wizard to create portal users from instances of 'res.partner'. The purpose
        is to provide an OpenERP database access to customers or suppliers.
    """
    _name = 'res.portal.wizard'
    _description = 'Portal Wizard'

    _columns = {
        'partner_id': fields.many2one('res.partner', required=True, string="Partner"),
        'portal_id': fields.many2one('res.portal', required=True,
            string='Portal',
            help="The portal in which new users must be added"),
        'user_ids': fields.one2many('res.portal.wizard.user', 'wizard_id',
            string='Users'),
        'message': fields.text(string='Invitation message',
            help="This text is included in the welcome email sent to the users"),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        partner_id = context.get('active_id', False)
        portal_id = context.get('portal_id', False)
        res = {}
        if not partner_id:
            return res

        if 'partner_id' in fields:
            res.update({'partner_id': partner_id})

        if 'user_ids' in fields and portal_id:
            user_ids = self.get_portal_users(cr, uid, [partner_id], portal_id, context=context)
            res.update({'user_ids': user_ids})            
        return res

      
    def onchange_portal_id(self, cr, uid, ids, partner_id, portal_id, context=None):
        if not portal_id:
            return {'value': {}}
        user_list = self.get_portal_users(cr, uid, [partner_id], portal_id, context=context)
        return {'value': {'user_ids': user_list}}


    def _search_portal_user(self, cr, uid, partner_id, portal_id, context=None):
        portal_users = self.pool.get('res.portal').browse(cr, uid, portal_id, context=context).group_id.users
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        user_ids = self.pool.get('res.users').search(cr, uid, [('partner_id','=', partner.id)])
        return [u.id for u in portal_users if u.id in user_ids]

    def _portal_user_dict(self, cr, uid, partner, portal_id, context=None):
        res = []
        for address in partner.child_ids:
            users = self._portal_user_dict(cr, uid, address, portal_id, context=context)
            res.extend(users)

        if partner.child_ids:
            return res

        #if partner.parent_id:
        #    lang = partner.parent_id.lang or 'en_US'
        #    company_id = partner.parent_id.id
        #else:
        #    lang = partner.lang or 'en_US'
        #    company_id = partner.id
        user = False
        portal_user_ids = self._search_portal_user(cr, uid, partner.id, portal_id, context=context)
        user_id = len(portal_user_ids) and portal_user_ids[0] or False
        if user_id:
            user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
        email = user and user.user_email or partner.email
        users = [{
               'name': user and user.name or partner.name,
               'user_email': extract_email(email),
               'lang': partner.lang or 'en_US',
               'partner_id': partner.id,
               'has_portal_user': user_id and True or False,
               'user_id': user_id
        }]
        res.extend(users)
        return res

    def get_portal_users(self, cr, uid, partner_ids, portal_id, context=None):
        users = []
        res_partner = self.pool.get('res.partner')
        for partner in res_partner.browse(cr, uid, partner_ids, context=context):
            users.extend(self._portal_user_dict(cr, uid, partner, portal_id, context=context))
        return users


    def action_manage_portal_access(self, cr, uid, ids, context=None):
        clone_context = context or {}
        clone_context['noshortcut'] = True           # prevent shortcut creation
        context = clone_context.copy()

        
        res_portal_user = self.pool.get('res.portal.wizard.user')
        for data in self.browse(cr, uid, ids, context=context):
            if not data.user_ids:
                raise osv.except_osv(_('User required'),
                _('Create atleast one user for portal.'))
            
            portal_user_ids = [user.id for user in data.user_ids]
            res_portal_user.manage_portal_access(cr, uid, portal_user_ids, context=context)
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
            string='Email',
            help="Will be used as user login.  "
                 "Also necessary to send the account information to new users"),
        'lang': fields.selection(_lang_get, required=True,
            string='Language',
            help="The language for the user's user interface"),
        'partner_id': fields.many2one('res.partner',
            string='Partner'),
        'has_portal_user':fields.boolean('Has portal access'),
        'user_id': fields.many2one('res.users', string="User")
    }

    def _check_email(self, cr, uid, ids):
        """ check syntax of email address """
        for wuser in self.browse(cr, uid, ids):
            if not email_re.match(wuser.user_email): return False
        return True

    _constraints = [
        (_check_email, 'Invalid email address', ['email']),
    ]

    _defaults = {
        'lang': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).partner_id.lang or 'en_US',
        'partner_id': lambda self, cr, uid, ctx: ctx.get('active_id', False),
    }

    def send_email(self, cr, uid, portal_user, context=None):
        #TODO: use email template
        res_users = self.pool.get('res.users')
        mail_message = self.pool.get('mail.message')
        user = res_users.browse(cr, ROOT_UID, uid, context)
        if not user.user_email:
            raise osv.except_osv(_('Email required'),
                _('You must have an email address in your User Preferences'
                  ' to send emails.'))

        record = portal_user.wizard_id
        subject_data = {
                'company': user.company_id.name,
        }
        body_data = {
                'portal': record.portal_id.name,
                'message': record.message or "",
                'url': record.portal_id.url or _("(missing url)"),
                'db': cr.dbname,
                'login': portal_user.user_id.login,
                'password': portal_user.user_id.password,
                'name': portal_user.user_id.name
        }
        body_data.update(subject_data)
        email_from = user.user_email
        email_to = portal_user.user_email
        subject = _(WELCOME_EMAIL_SUBJECT) % subject_data
        body = _(WELCOME_EMAIL_BODY) % body_data
        res = mail_message.schedule_with_attach(cr, uid, email_from , [email_to], subject, body, context=context)
        if not res:
            _logger.warning(
                'Failed to send email from %s to %s', email_from, email_to)
        return True 

    def create_new_user(self, cr, uid, portal_user, context=None):
        res_user = self.pool.get('res.users')
        portal = portal_user.wizard_id.portal_id
        action_id = portal.home_action_id and portal.home_action_id.id or False
        partner_id = portal_user.partner_id and portal_user.partner_id.id
        user_ids = res_user.search(cr, uid, [('partner_id','=',partner_id)])
        user_id = False
        if user_ids and len(user_ids):
            user_id = user_ids[0]
        if not user_id:
            value = {
                    'name': portal_user.name,
                    'login': portal_user.user_email,
                    'password': random_password(),
                    'user_email': portal_user.user_email,
                    'context_lang': portal_user.lang,
                    'share': True,
                    'action_id': action_id,
                    'partner_id': partner_id,
                    'groups_id': [(6, 0, [])],
            } 
            user_id = res_user.create(cr, ROOT_UID, value, context=context) 
            portal_user.write({'user_id': user_id}, context)
            self.send_email(cr, uid, portal_user, context=context)
        if user_id not in [u.id for u in portal.group_id.users]:
            portal.write({'users': [(4, user_id)]}, context=context)
        return user_id

    def link_portal_user(self, cr, uid, portal_user, context=None):
        portal = portal_user.wizard_id.portal_id
        return portal.write({'users': [(4, portal_user.user_id.id)]}, context=context)

    def unlink_portal_user(self, cr, uid, portal_user, context=None):
        portal = portal_user.wizard_id.portal_id
        return portal.write({'users': [(3, portal_user.user_id.id)]}, context=context)

    def unlink_user(self, cr, uid, user_id, context=None):
        #TODO: search portal groups
        res_user = self.pool.get('res.users')
        user = res_user.browse(cr, uid, user_id, context=context)
        if not user.groups_id:
            user.unlink(context=context)
        return True
    

    def manage_portal_access(self, cr, uid, ids, context=None):
        for portal_user in self.browse(cr, uid, ids, context=None):
            poral_id = portal_user.wizard_id.portal_id
            #create new user into portal if has_portal_user and not user
            if portal_user.has_portal_user and not portal_user.user_id:
                self.create_new_user(cr, uid, portal_user, context=context)
            #link to portal            
            if portal_user.has_portal_user and portal_user.user_id:
                self.link_portal_user(cr, uid, portal_user, context=context)
            #unlink existing user into portal
            if not portal_user.has_portal_user and portal_user.user_id:
                self.unlink_portal_user(cr, uid, portal_user, context=context)
                #drop user if it does not has any access in any portal.
                self.unlink_user(cr, uid, portal_user.user_id.id, context=context)
wizard_user()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
