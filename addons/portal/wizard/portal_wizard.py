# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tools.translate import _
from odoo.tools import email_normalize
from odoo.exceptions import UserError

from odoo import api, fields, models, Command


_logger = logging.getLogger(__name__)


class PortalWizard(models.TransientModel):
    """
        A wizard to manage the creation/removal of portal users.
    """

    _name = 'portal.wizard'
    _description = 'Grant Portal Access'

    def _default_partner_ids(self):
        partner_ids = self.env.context.get('default_partner_ids', []) or self.env.context.get('active_ids', [])
        contact_ids = set()
        for partner in self.env['res.partner'].sudo().browse(partner_ids):
            contact_partners = partner.child_ids.filtered(lambda p: p.type in ('contact', 'other')) | partner
            contact_ids |= set(contact_partners.ids)

        return [Command.link(contact_id) for contact_id in contact_ids]

    partner_ids = fields.Many2many('res.partner', string='Partners', default=_default_partner_ids)
    user_ids = fields.One2many('portal.wizard.user', 'wizard_id', string='Users', compute='_compute_user_ids', store=True, readonly=False)
    welcome_message = fields.Text('Invitation Message', help="This text is included in the email sent to new users of the portal.")

    @api.depends('partner_ids')
    def _compute_user_ids(self):
        for portal_wizard in self:
            portal_wizard.user_ids = [
                Command.create({
                    'partner_id': partner.id,
                    'email': partner.email,
                })
                for partner in portal_wizard.partner_ids
            ]

    @api.model
    def action_open_wizard(self):
        """Create a "portal.wizard" and open the form view.

        We need a server action for that because the one2many "user_ids" records need to
        exist to be able to execute an a button action on it. If they have no ID, the
        buttons will be disabled and we won't be able to click on them.

        That's why we need a server action, to create the records and then open the form
        view on them.
        """
        portal_wizard = self.create({})
        return portal_wizard._action_open_modal()

    def _action_open_modal(self):
        """Allow to keep the wizard modal open after executing the action."""
        return {
            'name': _('Portal Access Management'),
            'type': 'ir.actions.act_window',
            'res_model': 'portal.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class PortalWizardUser(models.TransientModel):
    """
        A model to configure users in the portal wizard.
    """

    _name = 'portal.wizard.user'
    _description = 'Portal User Config'

    wizard_id = fields.Many2one('portal.wizard', string='Wizard', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, readonly=True, ondelete='cascade')
    email = fields.Char('Email')

    user_id = fields.Many2one('res.users', string='User', compute='_compute_user_id', compute_sudo=True)
    login_date = fields.Datetime(related='user_id.login_date', string='Latest Authentication')
    is_portal = fields.Boolean('Is Portal', compute='_compute_group_details')
    is_internal = fields.Boolean('Is Internal', compute='_compute_group_details')
    email_state = fields.Selection([
        ('ok', 'Valid'),
        ('ko', 'Invalid'),
        ('exist', 'Already Registered')],
        string='Status', compute='_compute_email_state', default='ok')

    @api.depends('email')
    def _compute_email_state(self):
        portal_users_with_email = self.filtered(lambda user: email_normalize(user.email))
        (self - portal_users_with_email).email_state = 'ko'

        existing_users = self.env['res.users'].with_context(active_test=False).sudo().search_read(
            self._get_similar_users_domain(portal_users_with_email),
            self._get_similar_users_fields()
        )
        for portal_user in portal_users_with_email:
            if next((user for user in existing_users if self._is_portal_similar_than_user(user, portal_user)), None):
                portal_user.email_state = 'exist'
            else:
                portal_user.email_state = 'ok'

    @api.depends('partner_id')
    def _compute_user_id(self):
        for portal_wizard_user in self:
            user = portal_wizard_user.partner_id.with_context(active_test=False).user_ids
            portal_wizard_user.user_id = user[0] if user else False

    @api.depends('user_id', 'user_id.groups_id')
    def _compute_group_details(self):
        for portal_wizard_user in self:
            user = portal_wizard_user.user_id

            if user and user._is_internal():
                portal_wizard_user.is_internal = True
                portal_wizard_user.is_portal = False
            elif user and user.has_group('base.group_portal'):
                portal_wizard_user.is_internal = False
                portal_wizard_user.is_portal = True
            else:
                portal_wizard_user.is_internal = False
                portal_wizard_user.is_portal = False

    def action_grant_access(self):
        """Grant the portal access to the partner.

        If the partner has no linked user, we will create a new one in the same company
        as the partner (or in the current company if not set).

        An invitation email will be sent to the partner.
        """
        self.ensure_one()
        self._assert_user_email_uniqueness()

        if self.is_portal or self.is_internal:
            raise UserError(_('The partner "%s" already has the portal access.', self.partner_id.name))

        group_portal = self.env.ref('base.group_portal')
        group_public = self.env.ref('base.group_public')

        self._update_partner_email()
        user_sudo = self.user_id.sudo()

        if not user_sudo:
            # create a user if necessary and make sure it is in the portal group
            company = self.partner_id.company_id or self.env.company
            user_sudo = self.sudo().with_company(company.id)._create_user()

        if not user_sudo.active or not self.is_portal:
            user_sudo.write({'active': True, 'groups_id': [(4, group_portal.id), (3, group_public.id)]})
            # prepare for the signup process
            user_sudo.partner_id.signup_prepare()

        self.with_context(active_test=True)._send_email()

        return self.action_refresh_modal()

    def action_revoke_access(self):
        """Remove the user of the partner from the portal group.

        If the user was only in the portal group, we archive it.
        """
        self.ensure_one()
        if not self.is_portal:
            raise UserError(_('The partner "%s" has no portal access or is internal.', self.partner_id.name))

        group_portal = self.env.ref('base.group_portal')
        group_public = self.env.ref('base.group_public')

        self._update_partner_email()

        # Remove the sign up token, so it can not be used
        self.partner_id.sudo().signup_token = False

        user_sudo = self.user_id.sudo()

        # remove the user from the portal group
        if user_sudo and user_sudo.has_group('base.group_portal'):
            user_sudo.write({'groups_id': [(3, group_portal.id), (4, group_public.id)], 'active': False})

        return self.action_refresh_modal()

    def action_invite_again(self):
        """Re-send the invitation email to the partner."""
        self.ensure_one()
        self._assert_user_email_uniqueness()

        if not self.is_portal:
            raise UserError(_('You should first grant the portal access to the partner "%s".', self.partner_id.name))

        self._update_partner_email()
        self.with_context(active_test=True)._send_email()

        return self.action_refresh_modal()

    def action_refresh_modal(self):
        """Refresh the portal wizard modal and keep it open. Used as fallback action of email state icon buttons,
        required as they must be non-disabled buttons to fire mouse events to show tooltips on email state."""
        return self.wizard_id._action_open_modal()

    def _create_user(self):
        """ create a new user for wizard_user.partner_id
            :returns record of res.users
        """
        return self.env['res.users'].with_context(no_reset_password=True)._create_user_from_template({
            'email': email_normalize(self.email),
            'login': email_normalize(self.email),
            'partner_id': self.partner_id.id,
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, self.env.company.ids)],
        })

    def _send_email(self):
        """ send notification email to a new portal user """
        self.ensure_one()

        # determine subject and body in the portal user's language
        template = self.env.ref('portal.mail_template_data_portal_welcome')
        if not template:
            raise UserError(_('The template "Portal: new user" not found for sending email to the portal user.'))

        lang = self.user_id.sudo().lang
        partner = self.user_id.sudo().partner_id

        portal_url = partner.with_context(signup_force_type_in_url='', lang=lang)._get_signup_url_for_action()[partner.id]
        partner.signup_prepare()

        template.with_context(dbname=self._cr.dbname, portal_url=portal_url, lang=lang).send_mail(self.id, force_send=True)

        return True

    def _assert_user_email_uniqueness(self):
        """Check that the email can be used to create a new user."""
        self.ensure_one()
        if self.email_state == 'ko':
            raise UserError(_('The contact "%s" does not have a valid email.', self.partner_id.name))
        if self.email_state == 'exist':
            raise UserError(_('The contact "%s" has the same email as an existing user', self.partner_id.name))

    def _update_partner_email(self):
        """Update partner email on portal action, if a new one was introduced and is valid."""
        email_normalized = email_normalize(self.email)
        if self.email_state == 'ok' and email_normalize(self.partner_id.email) != email_normalized:
            self.partner_id.write({'email': email_normalized})

    def _get_similar_users_domain(self, portal_users_with_email):
        """ Returns the domain needed to find the users that have the same email
        as portal users.
        :param portal_users_with_email: portal users that have an email address.
        """
        normalized_emails = [email_normalize(portal_user.email) for portal_user in portal_users_with_email]
        return [('login', 'in', normalized_emails)]

    def _get_similar_users_fields(self):
        """ Returns a list of field elements to extract from users.
        """
        return ['id', 'login']

    def _is_portal_similar_than_user(self, user, portal_user):
        """ Checks if the credentials of a portal user and a user are the same
        (users are distinct and their emails are similar).
        """
        return user['login'] == email_normalize(portal_user.email) and user['id'] != portal_user.user_id.id
