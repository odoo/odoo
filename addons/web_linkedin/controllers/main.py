# -*- coding: utf-8 -*-
import simplejson
import urllib2
import werkzeug

from openerp.addons.web import http
from openerp.addons.web.http import request


class Linkedin(http.Controller):

    @http.route("/linkedin/authentication", type='http', auth="user")
    def authentication_callback(self, **kw):
        state = simplejson.loads(kw['state'])
        url_return = state.get('f')
        scope = state.get('d')
        linkedin_obj = request.env['linkedin']
        config_obj = request.env['ir.config_parameter'].sudo()
        api_key = config_obj.get_param('web.linkedin.apikey')
        secret_key = config_obj.get_param('web.linkedin.secretkey')
        uri = linkedin_obj.get_uri_oauth(a="accessToken")
        response_code = kw.get('code')
        base_url = config_obj.get_param('web.base.url')
        params = {
            'grant_type': 'authorization_code',
            'code': response_code,
            'redirect_uri': base_url + '/linkedin/authentication',
            'client_id': api_key,
            'client_secret': secret_key
        }
        if response_code:
            url = uri + "?%s" % werkzeug.url_encode(params)
            try:
                headers = {"Content-type": "application/x-www-form-urlencoded"}
                req = urllib2.Request(url, {}, headers)
                content = urllib2.urlopen(req).read()
                response = simplejson.loads(content)
                linkedin_obj.set_all_tokens(response)
                if scope:
                    linkedin_obj.sync_linkedin_contacts(url_return)
                return werkzeug.utils.redirect(url_return)
            except urllib2.HTTPError, e:
                return werkzeug.utils.redirect("%s%s%s" % (url_return, "?error=", e))
            except Exception, e:
                return werkzeug.utils.redirect("%s%s%s" % (url_return, "?error=", e))
        elif kw.get('error'):
            return werkzeug.utils.redirect("%s%s%s" % (url_return, "?error=", kw.get('error')))
        else:
            return werkzeug.utils.redirect("%s%s" % (url_return, "?error=Unknown_error"))

    @http.route("/linkedin/get_search_popup_data", type='json', auth="user")
    def get_search_popup_data(self, **post):
        linkedin_obj = request.env['linkedin']
        need_auth = linkedin_obj.with_context(post.get('local_context')).need_authorization()
        if not need_auth:
            return linkedin_obj.get_search_popup_data(**post)
        else:
            return {'status': 'need_auth', 'url': linkedin_obj.with_context(post.get('local_context'))._get_authorize_uri(from_url=post.get('from_url'))}

    @http.route("/linkedin/linkedin_logout", type='json', auth='user')
    def linkedin_logout(self, **post):
        #Revoking access token from database, no need to invalidate token using API
        #because there is no programmatic way to invalidate token(https://developer.linkedin.com/forum/revoke-authorization-access-token)
        return request.env.user.sudo().write({'linkedin_token': False, 'linkedin_token_validity': False})

    @http.route("/linkedin/sync_linkedin_contacts", type='json', auth='user')
    def sync_linkedin_contacts(self, **post):
        if not post:
            return False
        return request.env['linkedin'].with_context(post.get('local_context')).sync_linkedin_contacts(post.get('from_url'))


class Binary(http.Controller):
    @http.route('/web_linkedin/binary/url2binary', type='json', auth='user')
    def url2binary(self, url):
        """Used exclusively to load images from LinkedIn profiles, must not be used for anything else."""
        return request.env['linkedin'].url2binary(url)
