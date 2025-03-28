# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    website_id = fields.Many2one('website', related='partner_id.website_id', store=True, related_sudo=False, readonly=False)

    _sql_constraints = [
        # Partial constraint, complemented by a python constraint (see below).
        ('login_key', 'unique (login, website_id)', 'You can not have two users with the same login!'),
    ]

    @api.constrains('login', 'website_id')
    def _check_login(self):
        """ Do not allow two users with the same login without website """
        self.flush_model(['login', 'website_id'])
        self.env.cr.execute(
            """SELECT login
                 FROM res_users
                WHERE login IN (SELECT login FROM res_users WHERE id IN %s AND website_id IS NULL)
                  AND website_id IS NULL
             GROUP BY login
               HAVING COUNT(*) > 1
            """,
            (tuple(self.ids),)
        )
        if self.env.cr.rowcount:
            raise ValidationError(_('You can not have two users with the same login!'))

    @api.model
    def _get_login_domain(self, login):
        website = self.env['website'].get_current_website()
        return super(ResUsers, self)._get_login_domain(login) + website.website_domain()

    @api.model
    def _get_email_domain(self, email):
        website = self.env['website'].get_current_website()
        return super()._get_email_domain(email) + website.website_domain()

    @api.model
    def _get_login_order(self):
        return 'website_id, ' + super(ResUsers, self)._get_login_order()

    @api.model
    def _signup_create_user(self, values):
        current_website = self.env['website'].get_current_website()
        # Note that for the moment, portal users can connect to all websites of
        # all companies as long as the specific_user_account setting is not
        # activated.
        values['company_id'] = current_website.company_id.id
        values['company_ids'] = [Command.link(current_website.company_id.id)]
        if request and current_website.specific_user_account:
            values['website_id'] = current_website.id
        new_user = super(ResUsers, self)._signup_create_user(values)
        return new_user

    @api.model
    def _get_signup_invitation_scope(self):
        current_website = self.env['website'].sudo().get_current_website()
        return current_website.auth_signup_uninvited or super(ResUsers, self)._get_signup_invitation_scope()

    @classmethod
    def authenticate(cls, db, credential, user_agent_env):
        """ Override to link the logged in user's res.partner to website.visitor.
        If a visitor already exists for that user, assign it data from the
        current anonymous visitor (if exists).
        Purpose is to try to aggregate as much sub-records (tracked pages,
        leads, ...) as possible. """
        visitor_pre_authenticate_sudo = None
        if request and request.env:
            visitor_pre_authenticate_sudo = request.env['website.visitor']._get_visitor_from_request()
        auth_info = super().authenticate(db, credential, user_agent_env)
        if auth_info.get('uid') and visitor_pre_authenticate_sudo:
            env = api.Environment(request.env.cr, auth_info['uid'], {})
            # user may not always exist in request cursor for auto-provisioning modules like LDAP
            if not env.user.exists():
                return auth_info

            user_partner = env.user.partner_id
            visitor_current_user_sudo = env['website.visitor'].sudo().search([
                ('partner_id', '=', user_partner.id)
            ], limit=1)
            if visitor_current_user_sudo:
                # A visitor exists for the logged in user, link public
                # visitor records to it.
                if visitor_pre_authenticate_sudo != visitor_current_user_sudo:
                    visitor_pre_authenticate_sudo._merge_visitor(visitor_current_user_sudo)
                visitor_current_user_sudo._update_visitor_last_visit()
            else:
                visitor_pre_authenticate_sudo.access_token = user_partner.id
                visitor_pre_authenticate_sudo._update_visitor_last_visit()
        return auth_info

    @api.constrains('groups_id')
    def _check_one_user_type(self):
        super()._check_one_user_type()
        internal_users = self.env.ref('base.group_user').users & self
        if any(user.website_id for user in internal_users):
            raise ValidationError(_("Remove website on related partner before they become internal user."))
