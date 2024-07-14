# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from datetime import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join

from odoo import api, fields, models


class SocialAccountFacebook(models.Model):
    _inherit = 'social.account'

    facebook_account_id = fields.Char('Facebook Account ID', readonly=True,
        help="Facebook Page ID provided by the Facebook API, this should never be set manually.")
    facebook_access_token = fields.Char('Facebook Access Token', readonly=True,
        help="""Facebook Page Access Token provided by the Facebook API, this should never be set manually.
            It's used to authenticate requests when posting to or reading information from this account.""")

    def _compute_stats_link(self):
        """ External link to this Facebook Page's 'insights' (fancy name for the page statistics). """
        facebook_accounts = self._filter_by_media_types(['facebook'])
        super(SocialAccountFacebook, (self - facebook_accounts))._compute_stats_link()

        for account in facebook_accounts:
            account.stats_link = "https://www.facebook.com/%s/insights" % account.facebook_account_id \
                if account.facebook_account_id else False

    def _compute_statistics(self):
        """ This method computes this Facebook Page's statistics and trends.
        - The engagement and stories are a computed total of the last year of data for this account.
        - The audience is the all time total of fans (people liking) this page, as visible on the page stats.
          We actually need a separate request to fetch that information.
        - The trends are computed using the delta of the last 30 days compared to the (total - value of last 30 days).
          ex:
          - We gained 40 stories in the last 3 months.
          - We have 60 stories in total (last year of data).
          - The trend is 200% -> (40 / (60 - 40)) * 100 """

        facebook_accounts = self._filter_by_media_types(['facebook'])
        super(SocialAccountFacebook, (self - facebook_accounts))._compute_statistics()

        for account in facebook_accounts.filtered('facebook_account_id'):
            insights_endpoint_url = url_join(self.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, "%s/insights" % account.facebook_account_id)
            statistics_30d = account._compute_statistics_facebook(insights_endpoint_url)
            statistics_360d = account._compute_statistics_facebook_360d(insights_endpoint_url)

            page_global_stats = requests.get(url_join(self.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, account.facebook_account_id),
                params={
                    'fields': 'fan_count',
                    'access_token': account.facebook_access_token
                },
                timeout=5
            )

            account.write({
                'audience': page_global_stats.json().get('fan_count'),
                'audience_trend': self._compute_trend(account.audience, statistics_30d['page_fans']),
                'engagement': statistics_360d['page_post_engagements'],
                'engagement_trend': self._compute_trend(account.engagement, statistics_30d['page_post_engagements']),
                'stories': statistics_360d['page_content_activity'],
                'stories_trend': self._compute_trend(account.stories, statistics_30d['page_content_activity'])
            })

    def _compute_statistics_facebook_360d(self, insights_endpoint_url):
        """ Facebook only accepts requests for a range of maximum 90 days.
        We loop 4 times over 90 days to build the last 360 days of data (~ 1 year). """

        total_statistics = dict(page_post_engagements=0, page_content_activity=0, page_fans=0)
        for i in range(4):
            until = datetime.now() - relativedelta(days=(i * 90))
            since = until - relativedelta(days=90)
            statistics_90d = self._compute_statistics_facebook(
                insights_endpoint_url,
                since=int(since.timestamp()),
                until=int(until.timestamp())
            )
            total_statistics['page_post_engagements'] += statistics_90d['page_post_engagements']
            total_statistics['page_content_activity'] += statistics_90d['page_content_activity']
            total_statistics['page_fans'] += statistics_90d['page_fans']

        return total_statistics

    def _compute_statistics_facebook(self, endpoint_url, date_preset='last_30d', since=None, until=None):
        """ Check https://developers.facebook.com/docs/graph-api/reference/v17.0/insights for more information
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
            'metric': 'page_post_engagements,page_fan_adds,page_fan_removes,page_content_activity',
            'period': 'day',
            'access_token': self.facebook_access_token
        }

        if since and until:
            params['since'] = since
            params['until'] = until
        else:
            params['date_preset'] = date_preset

        response = requests.get(endpoint_url, params=params, timeout=5)

        statistics = {'page_fans': 0}
        if not response.json().get('data'):
            statistics.update({'page_post_engagements': 0, 'page_content_activity': 0})
            return statistics

        json_data = response.json().get('data')
        for metric in json_data:
            total_value = 0
            metric_values = metric.get('values')
            for value in metric_values:
                total_value += value.get('value')

            metric_name = metric.get('name')
            if metric_name in ['page_post_engagements', 'page_content_activity']:
                statistics[metric_name] = total_value
            elif metric_name == 'page_fan_adds':
                statistics['page_fans'] += total_value
            elif metric_name == 'page_fan_removes':
                statistics['page_fans'] -= total_value

        return statistics

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SocialAccountFacebook, self).create(vals_list)
        res.filtered(lambda account: account.media_type == 'facebook')._create_default_stream_facebook()
        return res

    def _create_default_stream_facebook(self):
        """ This will create a stream of type 'Page Posts' for each added accounts.
        It helps with onboarding to have your posts show up on the 'Feed' view as soon as you have configured your accounts."""

        if not self:
            return

        page_posts_stream_type = self.env.ref('social_facebook.stream_type_page_posts')
        streams_to_create = []
        for account in self:
            streams_to_create.append({
                'media_id': account.media_id.id,
                'stream_type_id': page_posts_stream_type.id,
                'account_id': account.id
            })
        self.env['social.stream'].create(streams_to_create)
