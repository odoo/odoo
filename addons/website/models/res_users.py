# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_website_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_website'),
        string='Website Editor', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_website')
    has_group_multi_website = fields.Boolean(
        'Multi-Websites',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='website.group_multi_website')

    _sql_constraints = [
        # this is done in Python because a SQL constraint like UNIQUE
        # (login, website_id) allows ('abc', NULL) and
        # ('abc', NULL) to coexist because of how SQL handles NULLs.
        ('login_key', 'CHECK (1=1)', 'You can not have two users with the same login!')
    ]

    @api.multi
    def _has_unsplash_key_rights(self):
        self.ensure_one()
        if self.has_group('website.group_website_designer'):
            return True
        return super(ResUsers, self)._has_unsplash_key_rights()

    @api.constrains('login', 'website_id')
    def _check_login(self):
        for user in self:
            if self.search([('id', '!=', user.id), ('login', '=', user.login)] + user.website_id.website_domain()):
                raise ValidationError(_('You can not have two users with the same login!'))

    @api.model
    def _get_login_domain(self, login):
        website = self.env['website'].get_current_website()
        return super(ResUsers, self)._get_login_domain(login) + website.website_domain()

    @api.model
    def _signup_create_user(self, values):
        new_user = super(ResUsers, self)._signup_create_user(values)
        new_user.website_id = self.env['website'].get_current_website()
        return new_user

    @api.model
    def _get_signup_invitation_scope(self):
        current_website = self.env['website'].get_current_website()
        return current_website.auth_signup_uninvited or super(ResUsers, self)._get_signup_invitation_scope()
