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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import email_re
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

# welcome email sent to portal users
# (note that calling '_' has no effect except exporting those strings for translation)
WELCOME_EMAIL_SUBJECT = _("Your OpenERP account at %(company)s")
WELCOME_EMAIL_BODY = _("""Dear %(name)s,

You have been given access to %(portal)s.

Your login account data is:
Database: %(db)s
Username: %(login)s

In order to complete the signin process, click on the following url:
%(url)s

%(welcome_message)s

--
OpenERP - Open Source Business Applications
http://www.openerp.com
""")


def extract_email(email):
    """ extract the email address from a user-friendly email address """
    m = email_re.search(email or "")
    return m and m.group(0) or ""



class wizard(osv.osv_memory):
    """
        A wizard to manage the creation/removal of portal users.
    """
    _name = 'portal.wizard'
    _description = 'Portal Access Management'

    _columns = {
        'portal_id': fields.many2one('res.groups', domain=[('is_portal', '=', True)], required=True,
            string='Portal', help="The portal that users can be added in or removed from."),
        'user_ids': fields.one2many('portal.wizard.user', 'wizard_id', string='Users'),
        'welcome_message': fields.text(string='Invitation Message',
            help="This text is included in the email sent to new users of the portal."),
    }

    def _default_portal(self, cr, uid, context):
        portal_ids = self.pool.get('res.groups').search(cr, uid, [('is_portal', '=', True)])
        return portal_ids and portal_ids[0] or False

    _defaults = {
        'portal_id': _default_portal,
    }

    def onchange_portal_id(self, cr, uid, ids, portal_id, context=None):
        # for each partner, determine corresponding portal.wizard.user records
        res_partner = self.pool.get('res.partner')
        partner_ids = context and context.get('active_ids') or []
        contact_ids = set()
        user_changes = []
        for partner in res_partner.browse(cr, SUPERUSER_ID, partner_ids, context):
            for contact in (partner.child_ids or [partner]):
                # make sure that each contact appears at most once in the list
                if contact.id not in contact_ids:
                    contact_ids.add(contact.id)
                    in_portal = False
                    if contact.user_ids:
                        in_portal = portal_id in [g.id for g in contact.user_ids[0].groups_id]
                    user_changes.append((0, 0, {
                        'partner_id': contact.id,
                        'email': contact.email,
                        'in_portal': in_portal,
                    }))
        return {'value': {'user_ids': user_changes}}

    def action_apply(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context)
        portal_user_ids = [user.id for user in wizard.user_ids]
        self.pool.get('portal.wizard.user').action_apply(cr, uid, portal_user_ids, context)
        return {'type': 'ir.actions.act_window_close'}

class wizard_user(osv.osv_memory):
    """
        A model to configure users in the portal wizard.
    """
    _name = 'portal.wizard.user'
    _description = 'Portal User Config'

    _columns = {
        'wizard_id': fields.many2one('portal.wizard', string='Wizard', required=True),
        'partner_id': fields.many2one('res.partner', string='Contact', required=True, readonly=True),
        'email': fields.char(size=240, string='Email'),
        'in_portal': fields.boolean('In Portal'),
    }

    def create(self, cr, uid, values, context=None):
        """ overridden to update the partner's email (if necessary) """
        id = super(wizard_user, self).create(cr, uid, values, context)
        wuser = self.browse(cr, uid, id, context)
        if wuser.partner_id.email != wuser.email:
            wuser.partner_id.write({'email': wuser.email})
        return id

    def action_apply(self, cr, uid, ids, context=None):
        for wizard_user in self.browse(cr, SUPERUSER_ID, ids, context):
            portal = wizard_user.wizard_id.portal_id
            user = self._retrieve_user(cr, SUPERUSER_ID, wizard_user, context)
            if wizard_user.in_portal:
                # create a user if necessary, and make sure it is in the portal group
                if not user:
                    user = self._create_user(cr, SUPERUSER_ID, wizard_user, context)
                if (not user.active) or (portal not in user.groups_id):
                    user.write({'active': True, 'groups_id': [(4, portal.id)]})
                    # prepare for the signup process
                    user.partner_id.signup_prepare()
                    wizard_user = self.browse(cr, SUPERUSER_ID, wizard_user.id, context)
                    self._send_email(cr, uid, wizard_user, context)
            else:
                # remove the user (if it exists) from the portal group
                if user and (portal in user.groups_id):
                    # if user belongs to portal only, deactivate it
                    if len(user.groups_id) <= 1:
                        user.write({'groups_id': [(3, portal.id)], 'active': False})
                    else:
                        user.write({'groups_id': [(3, portal.id)]})

    def _retrieve_user(self, cr, uid, wizard_user, context=None):
        """ retrieve the (possibly inactive) user corresponding to wizard_user.partner_id
            @param wizard_user: browse record of model portal.wizard.user
            @return: browse record of model res.users
        """
        if wizard_user.partner_id.user_ids:
            return wizard_user.partner_id.user_ids[0]
        # the user may be inactive, search for it
        res_users = self.pool.get('res.users')
        domain = [('partner_id', '=', wizard_user.partner_id.id), ('active', '=', False)]
        user_ids = res_users.search(cr, uid, domain)
        return user_ids and res_users.browse(cr, uid, user_ids[0], context) or False

    def _create_user(self, cr, uid, wizard_user, context=None):
        """ create a new user for wizard_user.partner_id
            @param wizard_user: browse record of model portal.wizard.user
            @return: browse record of model res.users
        """
        res_users = self.pool.get('res.users')
        create_context = dict(context or {}, noshortcut=True)       # to prevent shortcut creation
        values = {
            'login': extract_email(wizard_user.email),
            'partner_id': wizard_user.partner_id.id,
            'groups_id': [(6, 0, [])],
            'share': True,
        }
        user_id = res_users.create(cr, uid, values, context=create_context)
        return res_users.browse(cr, uid, user_id, context)

    def _send_email(self, cr, uid, wizard_user, context=None):
        """ send notification email to a new portal user
            @param wizard_user: browse record of model portal.wizard.user
            @return: the id of the created mail.mail record
        """
        this_context = context
        this_user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context)
        if not this_user.email:
            raise osv.except_osv(_('Email Required'),
                _('You must have an email address in your User Preferences to send emails.'))

        # determine subject and body in the portal user's language
        user = self._retrieve_user(cr, SUPERUSER_ID, wizard_user, context)
        context = dict(this_context or {}, lang=user.lang)
        data = {
            'company': this_user.company_id.name,
            'portal': wizard_user.wizard_id.portal_id.name,
            'welcome_message': wizard_user.wizard_id.welcome_message or "",
            'db': cr.dbname,
            'name': user.name,
            'login': user.login,
            'url': user.signup_url,
        }
        mail_mail = self.pool.get('mail.mail')
        mail_values = {
            'email_from': this_user.email,
            'email_to': user.email,
            'subject': _(WELCOME_EMAIL_SUBJECT) % data,
            'body_html': '<pre>%s</pre>' % (_(WELCOME_EMAIL_BODY) % data),
            'state': 'outgoing',
            'type': 'email',
        }
        mail_id = mail_mail.create(cr, uid, mail_values, context=this_context)
        return mail_mail.send(cr, uid, [mail_id], context=this_context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
