# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, tools
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    website_id = fields.Many2one('website', related='partner_id.website_id', store=True, related_sudo=False, readonly=False)

    _sql_constraints = [
        # Partial constraint, complemented by unique index (see below). Still
        # useful to keep because it provides a proper error message when a
        # violation occurs, as it shares the same prefix as the unique index.
        ('login_key', 'unique (login, website_id)', 'You can not have two users with the same login!'),
    ]

    @api.multi
    def _has_unsplash_key_rights(self):
        self.ensure_one()
        if self.has_group('website.group_website_designer'):
            return True
        return super(ResUsers, self)._has_unsplash_key_rights()

    @api.model
    def _get_login_domain(self, login):
        website = self.env['website'].get_current_website()
        return super(ResUsers, self)._get_login_domain(login) + website.website_domain()

    @api.model
    def _signup_create_user(self, values):
        current_website = self.env['website'].get_current_website()
        if request and current_website.specific_user_account:
            values['company_id'] = current_website.company_id.id
            values['company_ids'] = [(4, current_website.company_id.id)]
            values['website_id'] = current_website.id
        new_user = super(ResUsers, self)._signup_create_user(values)
        return new_user

    @api.model
    def _get_signup_invitation_scope(self):
        current_website = self.env['website'].get_current_website()
        return current_website.auth_signup_uninvited or super(ResUsers, self)._get_signup_invitation_scope()

    def _auto_init(self):
        result = super(ResUsers, self)._auto_init()
        # Use unique index to implement unique constraint per website, even if website_id is null
        # (not possible using a constraint)
        tools.create_unique_index(self._cr, 'res_users_login_key_unique_website_index',
            self._table, ['login', 'COALESCE(website_id,-1)'])
        return result
