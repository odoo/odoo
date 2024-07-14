# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, fields, api
from odoo.http import request

import logging
import requests

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """ A social.account represents an actual account on the related social.media.
    Ex: A Facebook Page or a Twitter Account.

    These social.accounts will then be used to send generic social.posts to multiple social.accounts.
    They are also used to display a 'dashboard' of statistics on the 'Feed' view.

    Account statistic fields are 'computed' manually through the _compute_statistics method
    that is overridden by each actual social module implementations (social_facebook, social_twitter, ...).
    The statistics computation is run manually when visualizing the Feed. """

    _name = 'social.account'
    _description = 'Social Account'

    def _get_default_company(self):
        """When the user is redirected to the callback URL of the different media,
        the company in the environment is always the company of the current user and not
        necessarily the selected company.

        So, before the authentication process, we store the selected company in the
        user session (see <social.media>::action_add_account) to be able to retrieve it
        here.
        """
        if request and 'social_company_id' in request.session:
            company_id = request.session['social_company_id']
            if not company_id:  # All companies
                return False
            if company_id in self.env.companies.ids:
                return company_id
        return self.env.company

    name = fields.Char('Name', required=True)
    social_account_handle = fields.Char("Handle / Short Name",
        help="Contains the social media handle of the person that created this account. E.g: '@odoo.official' for the 'Odoo' Twitter account")
    active = fields.Boolean("Active", default=True)
    media_id = fields.Many2one('social.media', string="Social Media", required=True, readonly=True,
        help="Related Social Media (Facebook, Twitter, ...).", ondelete='cascade')
    media_type = fields.Selection(related='media_id.media_type')
    stats_link = fields.Char("Stats Link", compute='_compute_stats_link',
        help="Link to the external Social Account statistics")
    image = fields.Image("Image", max_width=128, max_height=128, readonly=True)
    is_media_disconnected = fields.Boolean('Link with external Social Media is broken')

    audience = fields.Integer("Audience", readonly=True,
        help="General audience of the Social Account (Page Likes, Account Follows, ...).")
    audience_trend = fields.Float("Audience Trend", readonly=True, digits=(3, 0),
        help="Percentage of increase/decrease of the audience over a defined period.")
    engagement = fields.Integer("Engagement", readonly=True,
        help="Number of people engagements with your posts (Likes, Comments, ...).")
    engagement_trend = fields.Float("Engagement Trend", readonly=True, digits=(3, 0),
        help="Percentage of increase/decrease of the engagement over a defined period.")
    stories = fields.Integer("Stories", readonly=True,
        help="Number of stories created from your posts (Shares, Re-tweets, ...).")
    stories_trend = fields.Float("Stories Trend", readonly=True, digits=(3, 0),
        help="Percentage of increase/decrease of the stories over a defined period.")
    has_trends = fields.Boolean("Has Trends?",
        help="Defines whether this account has statistics tends or not.")
    has_account_stats = fields.Boolean("Has Account Stats", default=True,
        help="""Defines whether this account has Audience/Engagements/Stories stats.
        Account with stats are displayed on the dashboard.""")
    utm_medium_id = fields.Many2one('utm.medium', string="UTM Medium", required=True, ondelete='restrict',
        help="Every time an account is created, a utm.medium is also created and linked to the account")
    company_id = fields.Many2one('res.company', 'Company', default=_get_default_company,
                                 domain=lambda self: [('id', 'in', self.env.companies.ids)],
                                 help="Link an account to a company to restrict its usage or keep empty to let all companies use it.")

    def _compute_statistics(self):
        """ Every social module should override this method if it 'has_account_stats'.
        As the values depend on third party data, it's compute triggered manually that stores the data on the
        various stats fields (audience, engagement, stories) as well as related trends fields (if 'has_trends'). """
        pass

    def _compute_stats_link(self):
        """ Every social module should override this method.
        The 'stats_link' is an external link to the actual social.media statistics for this account.
        Ex: https://www.facebook.com/Odoo-Social-557894618055440/insights """
        for account in self:
            account.stats_link = False

    @api.depends('media_id')
    def _compute_display_name(self):
        """ ex: [Facebook] Odoo Social, [Twitter] Mitchell Admin, ... """
        for account in self:
            account.display_name = f"[{account.media_id.name}] {account.name if account.name else ''}"

    @api.model_create_multi
    def create(self, vals_list):
        """Every account has a unique corresponding utm.medium for statistics
        computation purposes. This way, it will be possible to see every leads
        or quotations generated through a particular account."""

        if all(vals.get('media_id') and vals.get('name') for vals in vals_list):
            # as 'media_id' and 'name' are required fields, we will let the 'create' handle the error
            # if they are not present
            media_all = self.env['social.media'].search([('id', 'in', [vals.get('media_id') for vals in vals_list])])
            media_names = {
                social_media.id: social_media.name
                for social_media in media_all
            }

            medium_all = self.env['utm.medium'].create([{
                "name": "[%(media_name)s] %(account_name)s" % {
                    "media_name": media_names.get(vals['media_id']),
                    "account_name": vals['name']
                }
            } for vals in vals_list])

            for vals, medium in zip(vals_list, medium_all):
                vals['utm_medium_id'] = medium.id

        res = super(SocialAccount, self).create(vals_list)
        res._compute_statistics()
        return res

    def write(self, vals):
        """ If name is updated, reflect the change on medium_id (see #create method). """
        if vals.get('name'):
            for social_account in self.filtered(lambda social_account: social_account.utm_medium_id):
                social_account.utm_medium_id.write({
                    'name': "[%(media_name)s] %(account_name)s" % {
                        "media_name": social_account.media_id.name,
                        "account_name": vals['name']
                    }
                })

        return super(SocialAccount, self).write(vals)

    @api.model
    def refresh_statistics(self):
        """ Will re-compute the statistics of all active accounts. """
        all_accounts = self.env['social.account'].search([('has_account_stats', '=', True)]).sudo()
        # As computing the statistics is a recurring task, we ignore occasional "read timeouts"
        # from the third-party services, as it would most likely mean a temporary slow connection
        # and/or a slow response from their side.
        try:
            all_accounts._compute_statistics()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.warning("Failed to refresh social account statistics.", exc_info=True)
        return [{
            'id': account.id,
            'name': account.name,
            'is_media_disconnected': account.is_media_disconnected,
            'audience': account.audience,
            'audience_trend': account.audience_trend,
            'engagement': account.engagement,
            'engagement_trend': account.engagement_trend,
            'stories': account.stories,
            'stories_trend': account.stories_trend,
            'has_trends': account.has_trends,
            'media_id': [account.media_id.id],
            'media_type': account.media_id.media_type,
            'stats_link': account.stats_link
        } for account in all_accounts]

    def _compute_trend(self, value, delta_30d):
        return 0.0 if value - delta_30d <= 0 else (delta_30d / (value - delta_30d)) * 100

    def _filter_by_media_types(self, media_types):
        return self.filtered(lambda account: account.media_type in media_types)

    def _get_multi_company_error_message(self):
        """Return an error message if the social accounts information can not be updated by the current user."""
        if not self.env.user.has_group('base.group_multi_company'):
            return

        cids = request.httprequest.cookies.get('cids')
        if cids:
            allowed_company_ids = {int(cid) for cid in cids.split(',')}
        else:
            allowed_company_ids = {self.env.company.id}

        accounts_other_companies = self.filtered(
            lambda account: account.company_id and account.company_id.id not in allowed_company_ids)

        if accounts_other_companies:
            return _(
                'Create other accounts for %(media_names)s for this company or ask %(company_names)s to share their accounts',
                media_names=', '.join(accounts_other_companies.mapped('media_id.name')),
                company_names=', '.join(accounts_other_companies.mapped('company_id.name')),
            )

    def _action_disconnect_accounts(self, disconnection_info=None):
        _logger.warning("Social account disconnected: %s. Reason: %s",
                        ", ".join(self.mapped("display_name")),
                        disconnection_info or "Not provided",
                        stack_info=True)
        self.sudo().write({'is_media_disconnected': True})
