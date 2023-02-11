# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class Users(models.Model):
    _inherit = 'res.users'

    def action_open_my_account_settings(self):
        action = {
            "name": _("Account Security"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "views": [[self.env.ref('auth_totp_mail.res_users_view_form').id, "form"]],
            "res_id": self.id,
        }
        return action

    def get_totp_invite_url(self):
        return '/web#action=auth_totp_mail.action_activate_two_factor_authentication'

    def action_totp_invite(self):
        invite_template = self.env.ref('auth_totp_mail.mail_template_totp_invite')
        users_to_invite = self.sudo().filtered(lambda user: not user.totp_secret)
        for user in users_to_invite:
            email_values = {
                'email_from': self.env.user.email_formatted,
                'author_id': self.env.user.partner_id.id,
            }
            invite_template.send_mail(user.id, force_send=True, email_values=email_values,
                                      notif_layout='mail.mail_notification_light')

        # Display a confirmation toaster
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': _("Invitation to use two-factor authentication sent for the following user(s): %s",
                             ', '.join(users_to_invite.mapped('name'))),
            }
        }
