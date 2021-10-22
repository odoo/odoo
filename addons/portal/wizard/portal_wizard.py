# -*- coding: utf-8 -*-
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
        self.refresh()
        return {
            'name': _('Portal Access Management'),
            'type': 'ir.actions.act_window',
            'res_model': 'portal.wizard',
            'view_type': 'form',
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

    @api.depends('partner_id')
    def _compute_user_id(self):
        for portal_wizard_user in self:
            user = portal_wizard_user.partner_id.with_context(active_test=False).user_ids
            portal_wizard_user.user_id = user[0] if user else False

    @api.depends('user_id', 'user_id.groups_id')
    def _compute_group_details(self):
        for portal_wizard_user in self:
            user = portal_wizard_user.user_id

            if user and user.has_group('base.group_user'):
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

        # update partner email, if a new one was introduced
        if not self.is_portal and not self.is_internal and self.partner_id.email != self.email:
            self.partner_id.write({'email': self.email})

        self.partner_id.action_grant_portal_access(self.wizard_id.welcome_message)
        return self.wizard_id._action_open_modal()

    def action_revoke_access(self):
        """Remove the user of the partner from the portal group.

        If the user was only in the portal group, we archive it.
        """
        self.ensure_one()

        # update partner email, if a new one was introduced
        if self.is_portal and self.partner_id.email != self.email:
            self.partner_id.write({'email': self.email})

        self.partner_id.action_revoke_portal_access()
        return self.wizard_id._action_open_modal()

    def action_invite_again(self):
        """Re-send the invitation email to the partner."""
        self.ensure_one()

        # update partner email, if a new one was introduced
        if self.is_portal and self.partner_id.email != self.email:
            self.partner_id.write({'email': self.email})

        self.partner_id.action_resend_portal_access_invitation(self.wizard_id.welcome_message)
        return self.wizard_id._action_open_modal()
