# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from datetime import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join

from odoo import api, fields, models


class SocialAccountInstagram(models.Model):
    _inherit = 'social.account'

    instagram_account_id = fields.Char('Instagram Account ID', readonly=True,
        help="Instagram Account ID provided by the Facebook API, this should never be set manually.")
    instagram_facebook_account_id = fields.Char('Instagram Facebook Account ID', readonly=True,
        help="""Facebook Account ID provided by the Facebook API, this should never be set manually.
        The Instagram ("Professional") account is always linked to a Facebook account.""")
    instagram_access_token = fields.Char(
        'Instagram Access Token', readonly=True,
        help="""Instagram Access Token provided by the Facebook API, this should never be set manually.
        It's used to authenticate requests when posting to or reading information from this account.""")

    def _compute_stats_link(self):
        """ Instagram does not provide a 'desktop' version of the insights.
        Statistics are only available through the mobile app, which means we don't have any website URL to provide. """
        instagram_accounts = self._filter_by_media_types(['instagram'])

        super(SocialAccountInstagram, (self - instagram_accounts))._compute_stats_link()

        for account in instagram_accounts:
            account.stats_link = False

    def _compute_statistics(self):
        """ Facebook Instagram API does not provide any data in the 'stories' department.
        Probably because the 'share' mechanic is not the same / not existing for Instagram posts. """
        instagram_accounts = self._filter_by_media_types(['instagram'])

        super(SocialAccountInstagram, (self - instagram_accounts))._compute_statistics()

        for account in instagram_accounts:
            insights_endpoint_url = url_join(
                self.env['social.media']._INSTAGRAM_ENDPOINT,
                "/v17.0/%s/insights" % account.instagram_account_id)
            statistics_30d = account._compute_statistics_instagram(insights_endpoint_url)
            statistics_360d = account._compute_statistics_instagram_360d(insights_endpoint_url)

            account_global_stats = requests.get(
                url_join(
                    self.env['social.media']._INSTAGRAM_ENDPOINT,
                    "/v17.0/%s" % account.instagram_account_id),
                params={
                    'fields': 'followers_count',
                    'access_token': account.instagram_access_token
                },
                timeout=5
            )

            audience = account_global_stats.json().get('followers_count', 0)
            account.write({
                'audience': audience,
                'audience_trend': self._compute_trend(audience, statistics_30d.get('follower_count', 0)),
                'engagement': statistics_360d.get('reach', 0),
                'engagement_trend': self._compute_trend(statistics_360d.get('reach', 0), statistics_30d.get('reach', 0)),
            })

    def _compute_statistics_instagram_360d(self, insights_endpoint_url):
        """ Instagram (Facebook) only accepts requests for a range of maximum 30 days.
        We loop 12 times over 30 days to build the last 360 days of data (~ 1 year). """

        total_statistics = dict(reach=0, follower_count=0)
        for index in range(12):
            until = datetime.now() - relativedelta(days=(index * 30))
            since = until - relativedelta(days=30)
            statistics_30d = self._compute_statistics_instagram(
                insights_endpoint_url,
                since=int(since.timestamp()),
                until=int(until.timestamp())
            )
            total_statistics['reach'] += statistics_30d.get('reach', 0)
            total_statistics['follower_count'] += statistics_30d.get('follower_count', 0)

        return total_statistics

    def _compute_statistics_instagram(self, endpoint_url, date_preset='last_30d', since=None, until=None):
        """ Check https://developers.facebook.com/docs/instagram-api/reference/ig-user/insights for more information
        about the endpoint used.
        e.g of data structure returned by the endpoint:
        [{
            'name':  'follower_count',
            'values': [{
                'value': 10,
            }, {
                'value': 20,
            }]
        }{
            'name':  'reach',
            'values': [{
                'value': 15,
            }, {
                'value': 25,
            }]
        }] """
        params = {
            'metric': 'reach,follower_count',
            'period': 'day',
            'access_token': self.instagram_access_token
        }

        if since and until:
            params['since'] = since
            params['until'] = until
        else:
            params['date_preset'] = date_preset

        response = requests.get(endpoint_url, params=params, timeout=5)

        statistics = {'follower_count': 0, 'reach': 0}
        if not response.json().get('data'):
            return statistics

        json_data = response.json().get('data')
        for metric in json_data:
            total_value = 0
            metric_values = metric.get('values')
            for value in metric_values:
                total_value += value.get('value')

            metric_name = metric.get('name')
            statistics[metric_name] = total_value

        return statistics

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SocialAccountInstagram, self).create(vals_list)
        res.filtered(
            lambda a: a.media_type == 'instagram'
        )._create_default_stream_instagram()
        return res

    def _create_default_stream_instagram(self):
        stream_type_instagram_posts = self.env.ref(
            'social_instagram.stream_type_instagram_posts')

        self.env['social.stream'].create([{
            'media_id': account.media_id.id,
            'stream_type_id': stream_type_instagram_posts.id,
            'account_id': account.id
        } for account in self])
