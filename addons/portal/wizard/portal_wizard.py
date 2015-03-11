# -*- coding: utf-8 -*-

import logging

from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.tools import email_split

_logger = logging.getLogger(__name__)

# welcome email sent to portal users
# (note that calling '_' has no effect except exporting those strings for translation)
WELCOME_EMAIL_SUBJECT = _("Your Odoo account at %(company)s")
WELCOME_EMAIL_BODY = _("""Dear %(name)s,

You have been given access to %(company)s's %(portal)s.

Your login account data is:
  Username: %(login)s
  Portal: %(portal_url)s
  Database: %(db)s 

You can set or change your password via the following url:
   %(signup_url)s

%(welcome_message)s

--
Odoo - Open Source Business Applications
http://www.openerp.com
""")


def extract_email(email):
    """ extract the email address from a user-friendly email address """
    addresses = email_split(email)
    return addresses[0] if addresses else ''



class Wizard(models.TransientModel):
    """
        A wizard to manage the creation/removal of portal users.
    """
    _name = 'portal.wizard'
    _description = 'Portal Access Management'

    def _default_portal(self):
        return self.env['res.groups'].search([('is_portal', '=', True)], limit=1)

    portal_id = fields.Many2one('res.groups', domain=[('is_portal', '=', True)], required=True,
        string='Portal', default=_default_portal, help="The portal that users can be added in or removed from.")
    user_ids = fields.One2many('portal.wizard.user', 'wizard_id', string='Users')
    welcome_message = fields.Text(string='Invitation Message',
        help="This text is included in the email sent to new users of the portal.")


    @api.onchange('portal_id')
    def onchange_portal_id(self):
        # for each partner, determine corresponding portal.wizard.user records
        partner_ids = self.env.context.get('active_ids')
        contact_ids = set()
        user_changes = []
        for partner in self.env['res.partner'].sudo().browse(partner_ids):
            for contact in (partner.child_ids or [partner]):
                # make sure that each contact appears at most once in the list
                if contact.id not in contact_ids:
                    contact_ids.add(contact.id)
                    in_portal = False
                    if contact.user_ids:
                        in_portal = self.portal_id.id in contact.user_ids.groups_id.ids
                    user_changes.append((0, 0, {
                        'partner_id': contact.id,
                        'email': contact.email,
                        'in_portal': in_portal,
                    }))
        self.user_ids = user_changes

    @api.multi
    def action_apply(self):
        self.ensure_one()
        self.user_ids.action_apply()
        return {'type': 'ir.actions.act_window_close'}

class WizardUser(models.TransientModel):
    """
        A model to configure users in the portal wizard.
    """
    _name = 'portal.wizard.user'
    _description = 'Portal User Config'

    wizard_id = fields.Many2one('portal.wizard', string='Wizard', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, readonly=True)
    email = fields.Char(string='Email', size=240)
    in_portal = fields.Boolean(string='In Portal')

    def get_error_messages(self):
        Users = self.env['res.users']
        emails = []
        error_empty = []
        error_emails = []
        error_user = []
        for wizard_user in self.sudo():
            if wizard_user.in_portal and not wizard_user._retrieve_user():
                email = extract_email(wizard_user.email)
                if not email:
                    error_empty.append(wizard_user.partner_id)
                elif email in emails and email not in error_emails:
                    error_emails.append(wizard_user.partner_id)
                user = Users.sudo().with_context(active_test=False).search([('login', '=', email)])
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

    def action_apply(self):
        error_msg = self.get_error_messages()
        if error_msg:
            raise UserError( "\n\n".join(error_msg))

        for wizard_user in self.sudo():
            portal = wizard_user.wizard_id.portal_id
            user = wizard_user._retrieve_user()
            if wizard_user.partner_id.email != wizard_user.email:
                wizard_user.partner_id.write({'email': wizard_user.email})
            if wizard_user.in_portal:
                # create a user if necessary, and make sure it is in the portal group
                if not user:
                    user = wizard_user._create_user()
                if (not user.active) or (portal not in user.groups_id):
                    user.write({'active': True, 'groups_id': [(4, portal.id)]})
                    # prepare for the signup process
                    user.partner_id.signup_prepare()
                wizard_user.refresh()
                wizard_user._send_email()
            else:
                # remove the user (if it exists) from the portal group
                if user and (portal in user.groups_id):
                    # if user belongs to portal only, deactivate it
                    if len(user.groups_id) <= 1:
                        user.write({'groups_id': [(3, portal.id)], 'active': False})
                    else:
                        user.write({'groups_id': [(3, portal.id)]})

    def _retrieve_user(self):
        """ retrieve the (possibly inactive) user corresponding to wizard_user.partner_id
            @param wizard_user: browse record of model portal.wizard.user
            @return: browse record of model res.users
        """
        domain = [('partner_id', '=', self.partner_id.id)]
        return self.env['res.users'].with_context(active_test=False).search(domain, limit=1)

    def _create_user(self):
        """ create a new user for wizard_user.partner_id
            @param wizard_user: browse record of model portal.wizard.user
            @return: browse record of model res.users
        """
       # to prevent shortcut creation
        values = {
            'email': extract_email(self.email),
            'login': extract_email(self.email),
            'partner_id': self.partner_id.id,
            'groups_id': [(6, 0, [])],
        }
        return self.env['res.users'].with_context(noshortcut=True, no_reset_password=True).create(values)

    def _send_email(self):
        """ send notification email to a new portal user
            @param wizard_user: browse record of model portal.wizard.user
            @return: the id of the created mail.mail record
        """
        if not self.env.user.email:
            raise UserError(_('You must have an email address in your User Preferences to send emails.'))

        # determine subject and body in the portal user's language
        user = self.sudo()._retrieve_user()
        portal_url = user.partner_id.with_context(signup_force_type_in_url='')._get_signup_url_for_action()[user.partner_id.id]
        user.partner_id.with_context(lang=user.lang).signup_prepare()

        data = {
            'company': self.env.user.company_id.name,
            'portal': self.wizard_id.portal_id.name,
            'welcome_message': self.wizard_id.welcome_message or "",
            'db': self.env.cr.dbname,
            'name': user.name,
            'login': user.login,
            'signup_url': user.signup_url,
            'portal_url': portal_url,
        }
        Mail = self.env['mail.mail']
        mail_values = {
            'email_from': self.env.user.email,
            'email_to': user.email,
            'subject': _(WELCOME_EMAIL_SUBJECT) % data,
            'body_html': '<pre>%s</pre>' % (_(WELCOME_EMAIL_BODY) % data),
            'state': 'outgoing',
            'type': 'email',
        }
        mail = Mail.create(mail_values)
        return Mail.send(mail)