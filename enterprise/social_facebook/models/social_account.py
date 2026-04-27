# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests

from datetime import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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
        - The engagement is a computed total of the last year of data for this account.
        - The audience is the all time total of fans (people liking) this page, as visible on the page stats.
          We actually need a separate request to fetch that information.
        - The trends are computed using the delta of the last 30 days compared to the (total - value of last 30 days).
          ex:
          - We gained 40 engagements in the last 3 months.
          - We have 60 engagements in total (last year of data).
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
            })

    def _compute_statistics_facebook_360d(self, insights_endpoint_url):
        """ Facebook only accepts requests for a range of maximum 90 days.
        We loop 4 times over 90 days to build the last 360 days of data (~ 1 year). """

        total_statistics = dict(page_post_engagements=0, page_fans=0)
        for i in range(4):
            until = datetime.now() - relativedelta(days=(i * 90))
            since = until - relativedelta(days=90)
            statistics_90d = self._compute_statistics_facebook(
                insights_endpoint_url,
                since=int(since.timestamp()),
                until=int(until.timestamp())
            )
            total_statistics['page_post_engagements'] += statistics_90d['page_post_engagements']
            total_statistics['page_fans'] += statistics_90d['page_fans']

        return total_statistics

    def _compute_statistics_facebook(self, endpoint_url, date_preset='last_30d', since=None, until=None):
        """ Check https://developers.facebook.com/docs/graph-api/reference/v17.0/insights for more information
        about the endpoint used.
        e.g of data structure returned by the endpoint:
        [{
            'name':  'page_post_engagements',
            'values': [{
                'value': 10,
                'end_time': '2025-08-20T07:00:00+0000'
            }, {
                'value': 20,
                'end_time': '2025-08-21T07:00:00+0000'
            }]
        }{
            'name':  'page_follows',
            'values': [{
                'value': 15,
                'end_time': '2025-08-20T07:00:00+0000'
            }, {
                'value': 25,
                'end_time': '2025-08-21T07:00:00+0000'
            }]
        }]

        That method returns the delta of the statistics in the given
        period of time (not the total value for the lifetime of the page).
        """

        params = {
            'metric': 'page_post_engagements,page_follows',
            'period': 'day',
            'access_token': self.facebook_access_token
        }

        if since and until:
            params['since'] = since
            params['until'] = until
        else:
            params['date_preset'] = date_preset

        response = requests.get(endpoint_url, params=params, timeout=5)

        statistics = {'page_fans': 0, 'page_post_engagements': 0}
        if not response.json().get('data'):
            _logger.warning("Social Facebook: Failed to retrieve page statistics: %s.", response.text)
            return statistics

        json_data = response.json().get('data')
        page_follows = {}
        for metric in json_data:
            metric_name = metric.get('name')
            values = metric.get('values') or []
            if metric_name == 'page_post_engagements':
                statistics['page_post_engagements'] += sum(v.get('value', 0) for v in values)
            elif metric_name == 'page_follows':
                page_follows.update({
                    v['end_time']: v['value']
                    for v in values
                    if 'end_time' in v and 'value' in v
                })

        if page_follows:
            # "Newest - Oldest"
            # Datetime is in "YYYY-MM-dd" format, so min / max work on string
            statistics['page_fans'] = page_follows[max(page_follows)] - page_follows[min(page_follows)]

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
