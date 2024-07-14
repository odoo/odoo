# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import requests
from datetime import datetime, timedelta
from urllib.parse import quote
from werkzeug.urls import url_join

from odoo import _, models, fields, api
from odoo.addons.social.controllers.main import SocialValidationException


class SocialAccountLinkedin(models.Model):
    _inherit = 'social.account'

    linkedin_account_urn = fields.Char('LinkedIn Account URN', readonly=True, help='LinkedIn Account URN')
    linkedin_account_id = fields.Char('LinkedIn Account ID', compute='_compute_linkedin_account_id')
    linkedin_access_token = fields.Char('LinkedIn access token', readonly=True, help='The access token is used to perform request to the REST API')

    @api.depends('linkedin_account_urn')
    def _compute_linkedin_account_id(self):
        """Depending on the used LinkedIn endpoint, we sometimes need the full URN, sometimes only the ID part.

        e.g.: "urn:li:person:12365" -> "12365"
        """
        for social_account in self:
            if social_account.linkedin_account_urn:
                social_account.linkedin_account_id = social_account.linkedin_account_urn.split(':')[-1]
            else:
                social_account.linkedin_account_id = False

    def _compute_stats_link(self):
        linkedin_accounts = self._filter_by_media_types(['linkedin'])
        super(SocialAccountLinkedin, (self - linkedin_accounts))._compute_stats_link()

        for account in linkedin_accounts:
            account.stats_link = 'https://www.linkedin.com/company/%s/admin/analytics/visitors/' % account.linkedin_account_id

    def _compute_statistics(self):
        linkedin_accounts = self._filter_by_media_types(['linkedin'])
        super(SocialAccountLinkedin, (self - linkedin_accounts))._compute_statistics()

        for account in linkedin_accounts:
            all_stats_dict = account._compute_statistics_linkedin()
            month_stats_dict = account._compute_statistics_linkedin(last_30d=True)
            # compute trend
            for stat_name in list(all_stats_dict.keys()):
                all_stats_dict['%s_trend' % stat_name] = self._compute_trend(all_stats_dict.get(stat_name, 0), month_stats_dict.get(stat_name, 0))
            # store statistics
            account.write(all_stats_dict)

    def _linkedin_fetch_followers_count(self):
        """Fetch number of followers from the LinkedIn API."""
        self.ensure_one()
        endpoint = url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'networkSizes/urn:li:organization:%s' % self.linkedin_account_id)
        # removing X-Restli-Protocol-Version header for this endpoint as it is not required according to LinkedIn Doc.
        # using this header with an endpoint that doesn't support it will cause the request to fail
        headers = self._linkedin_bearer_headers()
        headers.pop('X-Restli-Protocol-Version', None)
        response = requests.get(
            endpoint,
            params={'edgeType': 'COMPANY_FOLLOWED_BY_MEMBER'},
            headers=headers,
            timeout=3)
        if response.status_code != 200:
            return 0
        return response.json().get('firstDegreeSize', 0)

    def _compute_statistics_linkedin(self, last_30d=False):
        """Fetch statistics from the LinkedIn API.

        :param last_30d: If `True`, return the statistics of the last 30 days
                      Else, return the statistics of all the time.

            If we want statistics for the month, we need to choose the granularity
            "month". The time range has to be bigger than the granularity and
            if we have result over 1 month and 1 day (e.g.), the API will return
            2 results (one for the month and one for the day).
            To avoid this, we simply move the end date in the future, so we have
            result  only for this month, in one simple dict.
        """
        self.ensure_one()

        endpoint = url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'organizationalEntityShareStatistics')
        params = {
            'q': 'organizationalEntity',
            'organizationalEntity': self.linkedin_account_urn
        }

        if last_30d:
            # The LinkedIn API take timestamp in milliseconds
            end = int((datetime.now() + timedelta(days=2)).timestamp() * 1000)
            start = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
            endpoint += '?timeIntervals=%s' % '(timeRange:(start:%i,end:%i),timeGranularityType:MONTH)' % (start, end)

        response = requests.get(
            endpoint,
            params=params,
            headers=self._linkedin_bearer_headers(),
            timeout=5)

        if response.status_code != 200:
            return {}

        data = response.json().get('elements', [{}])[0].get('totalShareStatistics', {})

        return {
            'audience': self._linkedin_fetch_followers_count(),
            'engagement': data.get('clickCount', 0) + data.get('likeCount', 0) + data.get('commentCount', 0),
            'stories': data.get('shareCount', 0) + data.get('shareMentionsCount', 0),
        }

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SocialAccountLinkedin, self).create(vals_list)

        linkedin_accounts = res.filtered(lambda account: account.media_type == 'linkedin')
        if linkedin_accounts:
            linkedin_accounts._create_default_stream_linkedin()

        return res

    def _linkedin_bearer_headers(self, linkedin_access_token=None):
        if linkedin_access_token is None:
            linkedin_access_token = self.linkedin_access_token
        return {
            'Authorization': 'Bearer %s' % linkedin_access_token,
            'cache-control': 'no-cache',
            'X-Restli-Protocol-Version': '2.0.0',
            'LinkedIn-Version': '202401',
        }

    def _get_linkedin_accounts(self, linkedin_access_token):
        """Make an API call to get all LinkedIn pages linked to the actual access token."""
        response = self._linkedin_request(
            'organizationAcls',
            params={
                'q': 'roleAssignee',
                'role': 'ADMINISTRATOR',
                'state': 'APPROVED',
            },
            linkedin_access_token=linkedin_access_token,
        )
        if not response.ok:
            raise SocialValidationException(_('An error occurred when fetching your pages: %r.', response.text))

        account_ids = [
            organization['organization'].split(':')[-1]
            for organization in response.json().get('elements', [])
        ]

        response = self._linkedin_request(
            'organizations',
            object_ids=account_ids,
            fields=('id', 'name', 'localizedName', 'vanityName', 'logoV2:(original)'),
            linkedin_access_token=linkedin_access_token,
        )
        if not response.ok:
            raise SocialValidationException(_('An error occurred when fetching your pages data: %r.', response.text))

        organization_results = response.json().get('results', {})

        images_urns = [
            values.get('logoV2', {}).get('original')
            for values in organization_results.values()
        ]
        image_url_by_id = self._linkedin_request_images(images_urns, linkedin_access_token)

        accounts = []
        for account_id, organization in organization_results.items():
            image_id = organization.get('logoV2', {}).get('original', '').split(':')[-1]
            image_url = image_id and image_url_by_id.get(image_id)
            image_data = image_url and requests.get(image_url, timeout=10).content
            accounts.append({
                'name': organization.get('localizedName'),
                'linkedin_account_urn': f"urn:li:organization:{account_id}",
                'linkedin_access_token': linkedin_access_token,
                'social_account_handle': organization.get('vanityName'),
                'image': base64.b64encode(image_data) if image_data else False,
            })

        return accounts

    def _create_linkedin_accounts(self, access_token, media):
        linkedin_accounts = self._get_linkedin_accounts(access_token)
        if not linkedin_accounts:
            message = _('You need a Business Account to post on LinkedIn with Odoo Social.\n Please create one and make sure it is linked to your account')
            documentation_link = 'https://business.linkedin.com/marketing-solutions/linkedin-pages'
            documentation_link_label = _('Read More about Business Accounts')
            documentation_link_icon_class = 'fa fa-linkedin'
            raise SocialValidationException(message, documentation_link, documentation_link_label, documentation_link_icon_class)

        social_accounts = self.sudo().with_context(active_test=False).search([
            ('media_id', '=', media.id),
            ('linkedin_account_urn', 'in', [l.get('linkedin_account_urn') for l in linkedin_accounts])])

        error_message = social_accounts._get_multi_company_error_message()
        if error_message:
            raise SocialValidationException(error_message)

        existing_accounts = {
            account.linkedin_account_urn: account
            for account in social_accounts
            if account.linkedin_account_urn
        }

        accounts_to_create = []
        for account in linkedin_accounts:
            if account['linkedin_account_urn'] in existing_accounts:
                existing_accounts[account['linkedin_account_urn']].write({
                    'active': True,
                    'linkedin_access_token': account.get('linkedin_access_token'),
                    'social_account_handle': account.get('username'),
                    'is_media_disconnected': False,
                    'image': account.get('image')
                })
            else:
                account.update({
                    'media_id': media.id,
                    'is_media_disconnected': False,
                    'has_trends': True,
                    'has_account_stats': True,
                })
                accounts_to_create.append(account)

        self.create(accounts_to_create)

    def _create_default_stream_linkedin(self):
        """Create a stream for each organization page."""
        page_posts_stream_type = self.env.ref('social_linkedin.stream_type_linkedin_company_post')

        streams_to_create = [{
            'media_id': account.media_id.id,
            'stream_type_id': page_posts_stream_type.id,
            'account_id': account.id
        } for account in self if account.linkedin_account_urn]

        if streams_to_create:
            self.env['social.stream'].create(streams_to_create)

    def _extract_linkedin_picture_url(self, json_data):
        # TODO: remove in master
        return ''

    ################
    # External API #
    ################

    def _linkedin_request(self, endpoint, params=None, linkedin_access_token=None,
                          object_ids=None, fields=None, method="GET", json=None):
        if not linkedin_access_token:
            self.ensure_one()

        url = url_join(self.env['social.media']._LINKEDIN_ENDPOINT, endpoint)

        # need to be added manually, so requests doesn't escape them
        get_params = []
        if object_ids:
            get_params.append("ids=List(%s)" % ','.join(map(quote, object_ids)))
        if fields:
            get_params.append('fields=%s' % ','.join(fields))
        if get_params:
            url += "?" + "&".join(get_params)

        return requests.request(
            method,
            url,
            params=params,
            json=json,
            headers=self._linkedin_bearer_headers(linkedin_access_token),
            timeout=5,
        )

    def _linkedin_request_images(self, images_ids, linkedin_access_token=None):
        """Make an API call to get the downloadable URL of the images.

        :param images_ids: Image ids (li:image or digital asset)
        :param linkedin_access_token: Access token to use
        """
        images_urns = [
            f"urn:li:image:{images_id.split(':')[-1]}"
            for images_id in images_ids
            if images_id
        ]
        if not images_urns:
            return {}
        response = self._linkedin_request(
            'images',
            object_ids=images_urns,
            fields=('downloadUrl',),
            linkedin_access_token=linkedin_access_token,
        )
        return {
            image_urn.split(':')[-1]: image_values['downloadUrl']
            for image_urn, image_values in response.json().get('results', {}).items()
        } if response.ok else {}
