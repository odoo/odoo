# -*- coding: utf-8 -*-

from logging import getLogger

from odoo import http
from odoo.http import request
from odoo.tools import is_html_empty

_logger = getLogger(__name__)


class WebsiteTwitterWall(http.Controller):

    # Pagination after 15 tweet in storify view
    _tweet_per_page = 15

    @http.route('/twitter_walls', type='http', auth='public', website=True, sitemap=True)
    def twitter_wall_walls(self, **kwargs):
        return request.render('website_twitter_wall.twitter_walls', {
            'walls': request.env['website.twitter.wall'].search([('website_published', '=', True)] if request.env.uid == request.website.user_id.id else []),
            'is_html_empty': is_html_empty,
        })

    @http.route(['/twitter_wall/view/<model("website.twitter.wall"):wall>',
                 '/twitter_wall/view/<model("website.twitter.wall"):wall>/page/<int:page>'],
                type='http', auth='public', website=True, sitemap=True)
    def twitter_wall_view(self, wall, page=1, **kwargs):
        pager = request.website.pager(url='/twitter_wall/view/%s' % (wall.id), total=wall.total_tweets, page=page, step=self._tweet_per_page, scope=self._tweet_per_page)
        tweets = request.env['website.twitter.tweet'].search([('wall_ids', 'in', wall.id)], limit=self._tweet_per_page, offset=pager['offset'], order='id desc')
        return request.render('website_twitter_wall.twitter_wall_view', {
            'wall': wall,
            'tweets': tweets,
            'pager': pager,
            'is_html_empty': is_html_empty,
        })

    @http.route(['/twitter_wall/get_tweet/<model("website.twitter.wall"):wall>'], type='json', auth='public', website=True)
    def twitter_wall_get_tweet(self, wall, last_tweet_id):
        wall.sudo().fetch_tweets()
        return request.env['website.twitter.tweet'].search_read([('wall_ids', 'in', wall.id), ('id', '>', last_tweet_id)], ['tweet_id', 'tweet_html', 'wall_ids'], limit=15)
