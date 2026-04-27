# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.http import request
from odoo.tools import hmac


class SocialMedia(models.Model):
    """ A social.media represents the actual Media, ex: Facebook, Twitter, etc...
    As opposed to social.account that represents an existing account on this media.
    Ex: Odoo Social Facebook Page, Mitchell Admin Twitter Account, ...

    The social.media is used to store global media configuration (API keys, ...).
    It's also used to install the modules related to that social media (social_facebook, social_twitter, ...). """

    _name = 'social.media'
    _description = 'Social Media'
    _inherit = ['mail.thread']

    _DEFAULT_SOCIAL_IAP_ENDPOINT = 'https://social.api.odoo.com'

    name = fields.Char('Name', readonly=True, required=True, translate=True)
    media_description = fields.Char('Description', readonly=True)
    image = fields.Binary('Image', readonly=True)
    media_type = fields.Selection([], readonly=True,
        help="Used to make comparisons when we need to restrict some features to a specific media ('facebook', 'x', ...).")
    csrf_token = fields.Char('CSRF Token', compute='_compute_csrf_token',
        help="This token can be used to verify that an incoming request from a social provider has not been forged.")
    account_ids = fields.One2many('social.account', 'media_id', string="Social Accounts")
    accounts_count = fields.Integer('# Accounts', compute='_compute_accounts_count')
    has_streams = fields.Boolean('Streams Enabled', default=True, readonly=True, required=True,
        help="Controls if social streams are handled on this social media.")
    can_link_accounts = fields.Boolean('Can link accounts?', default=True, readonly=True, required=True,
        help="Controls if we can link accounts or not.")
    stream_type_ids = fields.One2many('social.stream.type', 'media_id', string="Stream Types")
    max_post_length = fields.Integer('Max Post Length',
        help="Set a maximum number of characters can be posted in post. 0 for no limit.")

    def _compute_accounts_count(self):
        for media in self:
            media.accounts_count = len(media.account_ids)

    def _compute_csrf_token(self):
        for media in self:
            media.csrf_token = hmac(self.env(su=True), 'social_social-account-csrf-token', media.id)

    def action_add_account(self, company_id=None):
        # Set the company of the futures new accounts (see <social.account>::_get_default_company)
        if company_id is None:
            company_id = self.env.company.id
        request.session['social_company_id'] = company_id
        return self._action_add_account()

    def _action_add_account(self):
        """ Every social module should override this method.
        Usually redirects to the social media links that allows accounts to be read by our app. """
        pass
