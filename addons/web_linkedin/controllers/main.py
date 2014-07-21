import base64
import simplejson
import urllib2
from urlparse import urlparse, urlunparse

import openerp
from openerp.addons.web import http
from openerp.http import request, Response
import werkzeug
import werkzeug.utils

class Linkedin(http.Controller):

    @http.route("/linkedin/authentication", type='http', auth="none")
    def authentication_callback(self, **kw):
        state = simplejson.loads(kw['state'])
        dbname = state.get('d')
        url_return = state.get('f')

        registry = openerp.modules.registry.RegistryManager.get(dbname)

        with registry.cursor() as cr:
            linkedin_obj = registry.get('linkedin')
            api_key = linkedin_obj.get_client_id(cr, request.session.uid, {})
            secret_key = linkedin_obj.get_client_secret(cr, request.session.uid, {})
            uri = linkedin_obj.get_uri_oauth(a="accessToken")
            response_code = kw.get('code')
            base_url = linkedin_obj.get_base_url(cr, request.session.uid, request.session.context)
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
                    linkedin_obj.set_all_tokens(cr, request.session.uid, response, {})
                    return werkzeug.utils.redirect(url_return)
                except urllib2.HTTPError, e:
                    return werkzeug.utils.redirect("%s%s%s" % (url_return ,"?error=" , e))
                except Exception, e:
                    return werkzeug.utils.redirect("%s%s%s" % (url_return ,"?error=" , e))
            elif kw.get('error'):
                return werkzeug.utils.redirect("%s%s%s" % (url_return ,"?error=" , kw.get('error')))
            else:
                return werkzeug.utils.redirect("%s%s" % (url_return ,"?error=Unknown_error"))

    @http.route("/linkedin/get_search_popup_data", type='json', auth="none")
    def get_search_popup_data(self, **post):
        linkedin_obj = request.registry['linkedin']
        need_auth = linkedin_obj.need_authorization(request.cr, request.session.uid, context=post.get('local_context'))
        if not need_auth:
            return linkedin_obj.get_search_popup_data(request.cr, request.session.uid, **post)
        else:
            return {'status': 'need_auth', 'url': linkedin_obj._get_authorize_uri(request.cr, request.session.uid, from_url=post.get('from_url'), context=post.get('local_context'))}

    @http.route("/linkedin/linkedin_logout", type='json', auth='none')
    def linkedin_logout(self, **post):
        #Revoking access token from database, no need to invalidate token using API
        #because there is no programmatic way to invalidate token(https://developer.linkedin.com/forum/revoke-authorization-access-token)
        linkedin_obj = request.registry['linkedin']
        return linkedin_obj.destroy_token(request.cr, request.session.uid)

    @http.route("/linkedin/sync_linkedin_contacts", type='json', auth='none')
    def sync_linkedin_contacts(self, **post):
        linkedin_obj = request.registry['linkedin']
        return linkedin_obj.sync_linkedin_contacts(request.cr, request.session.uid, post.get('from_url'), context=post.get('local_context'))

class Binary(http.Controller):
    @openerp.http.route('/web_linkedin/binary/url2binary', type='json', auth='user')
    def url2binary(self, url):
        """Used exclusively to load images from LinkedIn profiles, must not be used for anything else."""
        linkedin_obj = request.registry['linkedin']
        return linkedin_obj.url2binary(url)
