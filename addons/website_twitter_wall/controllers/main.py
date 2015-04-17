# -*- coding: utf-8 -*-
import logging
from base64 import encodestring
from urllib2 import Request, urlopen
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website_twitter_wall.models.oauth import Oauth
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class WebsiteTwitterWall(http.Controller):
    # Pagination after 10 tweet in storify view
    _tweet_per_page = 10

    def _set_viewed_wall(self, wall):
        """ Bind total views with session """
        wall_key = '%s_%s' % (wall.id, request.session_id)
        viewed_walls = request.session.setdefault(wall_key, list())
        if wall.id not in viewed_walls:
            wall.sudo().total_views += 1
            viewed_walls.append(wall.id)
            request.session[wall_key] = viewed_walls
        return True

    def _read_image(self, url):
        return encodestring(urlopen(url).read())

    @http.route('/twitter_wall/create', type='json', auth='user', methods=['POST'], website=True)
    def twitter_wall_create(self, **kargs):
        """ Create new wall """
        try:
            values = dict((value, kargs[value]) for value in ['name', 'description', 'image', 'website_published', 'tweetus_ids'] if kargs.get(value))
            if kargs['is_url']:
                values['image'] = self._read_image(values['image'])
            request.env['twitter.agent'].create(values)
        except Exception as e:
            _logger.error(e)
            return {'error': _('Internal server error, please try again later or contact administrator.\nHere is the error message: %s' % e.message)}
        return True

    @http.route('/twitter_walls', type='http', auth='public', website=True)
    def twitter_wall_walls(self, **kwargs):
        """ Display all walls """
        return request.website.render('website_twitter_wall.twitter_walls', {
            'walls': request.env['twitter.agent'].search([('website_published', '=', True)] if request.env.uid == request.website.user_id.id else [])
        })

    @http.route(['/twitter_wall/view/<model("twitter.agent"):wall>',
                '/twitter_wall/view/<model("twitter.agent"):wall>/page/<int:page>'], type='http', auth='public', website=True)
    def twitter_wall_view(self, wall, page=1, **kwargs):
        """ Storify and Live view of wall (include pagination in storify) """
        if not wall.auth_user:
            return http.local_redirect('/twitter_wall/authenticate/%s' % wall.id)
        TwitterTweet = request.env['twitter.tweet']
        domain = [('agent_id', '=', wall.id)]
        pager = request.website.pager(url='/twitter_wall/view/%s' % (wall.id), total=TwitterTweet.search_count(domain), page=page,
                                      step=self._tweet_per_page, scope=self._tweet_per_page)
        tweets = TwitterTweet.search(domain, limit=self._tweet_per_page, offset=pager['offset'], order='id desc')
        self._set_viewed_wall(wall)
        return request.website.render('website_twitter_wall.twitter_wall_view', {
            'wall': wall,
            'tweets': tweets,
            'pager': pager
        })

    @http.route(['/twitter_wall/authenticate/<model("twitter.agent"):wall>'], type='http', auth='user', website=True)
    def twitter_wall_authenticate(self, wall):
        """ Authenticate twitter account """
        auth = Oauth(wall.stream_id.twitter_api_key, wall.stream_id.twitter_api_secret)
        callback_url = '%s/%s/%s' % (request.env['ir.config_parameter'].get_param('web.base.url'), 'twitter_wall/callback', wall.id)
        HEADER = auth._generate_header(auth.REQUEST_URL, 'HMAC-SHA1', '1.0', callback_url=callback_url)
        HTTP_REQUEST = Request(auth.REQUEST_URL)
        HTTP_REQUEST.add_header('Authorization', HEADER)
        request_response = urlopen(HTTP_REQUEST, '').read()
        request_response = auth._string_to_dict(request_response)
        if request_response['oauth_token'] and request_response['oauth_callback_confirmed']:
            url = auth.AUTHORIZE_URL + '?oauth_token=' + request_response['oauth_token']
        return request.redirect(url)

    @http.route('/twitter_wall/callback/<model("twitter.agent"):wall>', type='http', auth='user')
    def twitter_wall_callback(self, wall, **kwargs):
        """ Return to this method if authorize app is success or cancel(denied kwargs) """
        if not kwargs.get('denied'):
            auth = Oauth(wall.stream_id.twitter_api_key, wall.stream_id.twitter_api_secret)
            access_token_response = Oauth._access_token(auth, kwargs.get('oauth_token'), kwargs.get('oauth_verifier'))
            wall.write({
                'twitter_access_token': access_token_response['oauth_token'],
                'twitter_access_token_secret': access_token_response['oauth_token_secret'],
                'auth_user': access_token_response['user_id']
            })
            wall.stream_id.restart()
            return http.local_redirect('/twitter_wall/view/%s' % (wall.id))
        return http.local_redirect('/twitter_walls')

    @http.route(['/twitter_wall/delete/<model("twitter.agent"):wall>'], type='http', auth='user', website=True)
    def twitter_wall_delete(self, wall):
        """ Delete wall """
        wall.unlink()
        return http.local_redirect('/twitter_walls')

    @http.route(['/twitter_wall/cover'], type='json', auth='user', website=True)
    def twitter_wall_cover(self, wall_id, url):
        """ Change image of cover """
        wall = request.env['twitter.agent'].browse(int(wall_id))
        if wall:
            return wall.write({'image': self._read_image(url) if not url == 'none' else True})

    @http.route(['/twitter_wall/get_tweet'], type='json', auth='public', website=True)
    def twitter_wall_get_tweet(self, domain, fields, limit=5):
        """ Get tweets """
        return request.env['twitter.tweet'].search_read(domain, fields, limit=limit)

    @http.route(['/twitter_wall/get_stream_state'], type='json', auth='public', website=True)
    def twitter_wall_get_stream_state(self, domain):
        """ Get stream state """
        Wall = request.env['twitter.agent'].search(domain, limit=1)
        if Wall.stream_id.state == 'stop':
            Wall.stream_id.restart()
        return Wall.stream_id.state
