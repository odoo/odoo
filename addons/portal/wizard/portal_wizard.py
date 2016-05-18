# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import email_split
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

# welcome email sent to portal users
# (note that calling '_' has no effect except exporting those strings for translation)


def extract_email(email):
    """ extract the email address from a user-friendly email address """
    addresses = email_split(email)
    return addresses[0] if addresses else ''



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
        'wizard_id': fields.many2one('portal.wizard', string='Wizard', required=True, ondelete='cascade'),
        'partner_id': fields.many2one('res.partner', string='Contact', required=True, readonly=True),
        'email': fields.char(string='Email', size=240),
        'in_portal': fields.boolean('In Portal'),
        'user_id': fields.many2one('res.users', string='Login User'),
    }

    def get_error_messages(self, cr, uid, ids, context=None):
        res_users = self.pool.get('res.users')
        emails = []
        error_empty = []
        error_emails = []
        error_user = []
        ctx = dict(context or {}, active_test=False)
        for wizard_user in self.browse(cr, SUPERUSER_ID, ids, ctx):
            if wizard_user.in_portal and not wizard_user.partner_id.user_ids:
                email = extract_email(wizard_user.email)
                if not email:
                    error_empty.append(wizard_user.partner_id)
                elif email in emails and email not in error_emails:
                    error_emails.append(wizard_user.partner_id)
                user = res_users.search(cr, SUPERUSER_ID, [('login', '=', email)], context=ctx)
                if user:
                    error_user.append(wizard_user.partner_id)
                emails.append(email)

        error_msg = []
        if error_empty:
            error_msg.append("%s\n- %s" % (_("Some contacts don't have a valid email: "),
                                '\n- '.join(['%s' % (p.display_name,) for p in error_empty])))
        if error_emails:
            error_msg.append("%s\n- %s" % (_("Several contacts have the same email: "),
                                '\n- '.join([p.email for p in error_emails])))
        if error_user:
            error_msg.append("%s\n- %s" % (_("Some contacts have the same email as an existing portal user:"),
                                '\n- '.join(['%s <%s>' % (p.display_name, p.email) for p in error_user])))
        if error_msg:
            error_msg.append(_("To resolve this error, you can: \n"
                "- Correct the emails of the relevant contacts\n"
                "- Grant access only to contacts with unique emails"))
        return error_msg

    def action_apply(self, cr, uid, ids, context=None):
        error_msg = self.get_error_messages(cr, uid, ids, context=context)
        if error_msg:
            raise UserError( "\n\n".join(error_msg))

        for wizard_user in self.browse(cr, SUPERUSER_ID, ids, dict(context, active_test=False)):
            portal = wizard_user.wizard_id.portal_id
            user = wizard_user.partner_id.user_ids and wizard_user.partner_id.user_ids[0] or False
            if wizard_user.partner_id.email != wizard_user.email:
                wizard_user.partner_id.write({'email': wizard_user.email})
            if wizard_user.in_portal:
                user_id = False
                # create a user if necessary, and make sure it is in the portal group
                if not user:
                    user_id = self._create_user(cr, SUPERUSER_ID, wizard_user.id, context)
                else:
                    user_id = user.id
                wizard_user.write({'user_id': user_id})
                if (not wizard_user.user_id.active) or (portal not in wizard_user.user_id.groups_id):
                    wizard_user.user_id.write({'active': True, 'groups_id': [(4, portal.id)]})
                    # prepare for the signup process
                    wizard_user.user_id.partner_id.signup_prepare()
                    self._send_email(cr, uid, wizard_user.id, context)
                wizard_user.refresh()
            else:
                # remove the user (if it exists) from the portal group
                if user and (portal in user.groups_id):
                    # if user belongs to portal only, deactivate it
                    if len(user.groups_id) <= 1:
                        user.write({'groups_id': [(3, portal.id)], 'active': False})
                    else:
                        user.write({'groups_id': [(3, portal.id)]})

    def _create_user(self, cr, uid, ids, context=None):
        """ create a new user for wizard_user.partner_id
            @param wizard_user: browse record of model portal.wizard.user
            @return: browse record of model res.users
        """
        wizard_user = self.browse(cr, uid, ids, context=context)
        res_users = self.pool.get('res.users')
        create_context = dict(context or {}, noshortcut=True, no_reset_password=True)       # to prevent shortcut creation
        values = {
            'email': extract_email(wizard_user.email),
            'login': extract_email(wizard_user.email),
            'partner_id': wizard_user.partner_id.id,
            'groups_id': [(6, 0, [])],
        }
        return res_users.create(cr, uid, values, context=create_context)

    def _send_email(self, cr, uid, ids, context=None):
        """ send notification email to a new portal user
            @param wizard_user: browse record of model portal.wizard.user
            @return: the id of the created mail.mail record
        """
        wizard_user = self.browse(cr, uid, ids, context=context)
        res_partner = self.pool['res.partner']
        this_user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context)
        if not this_user.email:
            raise UserError(_('You must have an email address in your User Preferences to send emails.'))

        # determine subject and body in the portal user's language
        user = wizard_user.user_id
        context = dict(context or {}, lang=user.lang)
        ctx_portal_url = dict(context, signup_force_type_in_url='')
        portal_url = res_partner._get_signup_url_for_action(cr, uid,
                                                            [user.partner_id.id],
                                                            context=ctx_portal_url)[user.partner_id.id]
        res_partner.signup_prepare(cr, uid, [user.partner_id.id], context=context)

        context.update({'dbname': cr.dbname, 'portal_url': portal_url})
        template_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'portal.mail_template_data_portal_welcome')
        if template_id:
            self.pool['mail.template'].send_mail(cr, uid, template_id, wizard_user.id, force_send=True, context=context)
        else:
            _logger.warning("No email template found for sending email to the portal user")
        return True
