# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models
from odoo.exceptions import UserError
from odoo.tools import email_normalize
from odoo.tools.translate import _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def can_edit_vat(self):
        ''' `vat` is a commercial field, synced between the parent (commercial
        entity) and the children. Only the commercial entity should be able to
        edit it (as in backend). '''
        return not self.parent_id

    def _send_portal_user_invitation_email(self, welcome_message=False):
        """ send notification email to a new portal user """
        self.ensure_one()
        user = self.user_ids[0] if self.user_ids else False

        if not user:
            raise UserError(_('You should grant portal access to the partner "%s" before sending him the invitation email.',
                self.name))

        # determine subject and body in the portal user's language
        template = self.env.ref('portal.mail_template_data_portal_welcome')
        if not template:
            raise UserError(_('The template "Portal: new user" not found for sending email to the portal user.'))

        lang = self.lang

        portal_url = self.with_context(signup_force_type_in_url='', lang=lang)._get_signup_url_for_action()[self.id]
        self.signup_prepare()

        template.with_context(dbname=self._cr.dbname, portal_url=portal_url, lang=lang,
            welcome_message=welcome_message).send_mail(user.id, force_send=True)

        return True

    def _assert_user_email_uniqueness(self):
        """Check that the email can be used to create a new user."""
        self.ensure_one()

        email = email_normalize(self.email)

        if not email:
            raise UserError(_('The contact "%s" does not have a valid email.', self.name))

        partner_user_ids = self.with_context(active_test=False).user_ids

        user = self.env['res.users'].sudo().with_context(active_test=False).search([
            ('id', '!=', partner_user_ids[0].id if partner_user_ids else False),
            ('login', '=ilike', email),
        ])

        if user:
            raise UserError(_('The contact "%s" has the same email as an existing user (%s).', self.name, user.name))

    def _create_user(self):
        """ create a new user for this partner
            :returns record of res.users
        """
        return self.env['res.users'].with_context(no_reset_password=True)._create_user_from_template({
            'email': email_normalize(self.email),
            'login': email_normalize(self.email),
            'partner_id': self.id,
            'company_id': self.env.company.id,
            'company_ids': [Command.set(self.env.company.ids)],
        })

    def action_grant_portal_access(self, welcome_message=False):
        """Grant the portal access to the partner.

        If the partner has no linked user, we will create a new one in the same company
        as the partner (or in the current company if not set).

        An invitation email will be sent to the partner.
        """
        self.ensure_one()
        self._assert_user_email_uniqueness()

        group_portal = self.env.ref('base.group_portal')
        group_public = self.env.ref('base.group_public')

        partner_user_ids = self.with_context(active_test=False).user_ids
        user = partner_user_ids[0] if partner_user_ids else False

        if user and (user.has_group('base.group_portal') or user.has_group('base.group_user')):
            raise UserError(_('The partner "%s" already has the portal access.', self.name))

        if not user:
            # create a user if necessary and make sure it is in the portal group
            company = self.company_id or self.env.company
            user_sudo = self.sudo().with_company(company.id)._create_user()
        else:
            user_sudo = user.sudo()

        if not user_sudo.active or not user_sudo.has_group('base.group_portal'):
            user_sudo.write({'active': True, 'groups_id': [Command.link(group_portal.id), Command.unlink(group_public.id)]})
            # prepare for the signup process
            self.signup_prepare()

        self.with_context(active_test=True)._send_portal_user_invitation_email(welcome_message)

    def action_resend_portal_access_invitation(self, welcome_message=False):
        """Re-send the invitation email to the partner."""
        self.ensure_one()

        user = self.user_ids[0] if self.user_ids else False

        if not user or not (user.has_group('base.group_portal')):
            raise UserError(_('You should first grant the portal access to the partner "%s".', self.name))

        self.with_context(active_test=True)._send_portal_user_invitation_email(welcome_message)

    def action_revoke_portal_access(self):
        """Remove the user of the partner from the portal group.

        If the user was only in the portal group, we archive it.
        """
        self.ensure_one()
        self._assert_user_email_uniqueness()

        user = self.user_ids[0] if self.user_ids else False

        if not user or not (user.has_group('base.group_portal')):
            raise UserError(_('The partner "%s" has no portal access.', self.name))

        group_portal = self.env.ref('base.group_portal')
        group_public = self.env.ref('base.group_public')

        # Remove the sign up token, so it can not be used
        self.sudo().signup_token = False

        user_sudo = user.sudo()

        # remove the user from the portal group
        if user_sudo and user_sudo.has_group('base.group_portal'):
            # if user belongs to portal only, deactivate it
            if len(user_sudo.groups_id) <= 1:
                user_sudo.write({'groups_id': [Command.unlink(group_portal.id), Command.link(group_public.id)], 'active': False})
            else:
                user_sudo.write({'groups_id': [Command.unlink(group_portal.id), Command.link(group_public.id)]})
