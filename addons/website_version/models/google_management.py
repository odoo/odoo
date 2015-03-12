# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import logging
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import Warning
from openerp import models, exceptions, api
from openerp.tools.translate import _
import simplejson

_logger = logging.getLogger(__name__)


class google_management(models.AbstractModel):

    STR_SERVICE = 'management'

    _name = 'google.%s' % STR_SERVICE

    @api.model
    def generate_data(self, experiment, isCreating=False):
        
        return {
            'name': experiment['name'],
            'status': experiment['status'],
            'variations': experiment['variations']
        }

    @api.model
    def create_an_experiment(self, data, website_id):
        gs_pool = self.env['google.service']
        website = self.env['website'].browse(website_id)[0]
        webPropertyId = website.google_analytics_key
        action_id = self.env['ir.model.data'].xmlid_to_res_id('website_version.action_website_view')
        if not webPropertyId:
            raise exceptions.RedirectWarning('Click on the website you want to make A/B testing and configure the Google Analytics Key and View ID', action_id, 'go to the websites menu')
        accountId = webPropertyId.split('-')[1]
        profileId = website.google_analytics_view_id
        if not profileId:
            raise exceptions.RedirectWarning('Click on the website you want to make A/B testing and configure the Google Analytics Key and View ID', action_id, 'go to the websites menu')
        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments?access_token=%s' % (accountId, webPropertyId, profileId, self.get_token())
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)
        try:
            x = gs_pool._do_request(url, data_json, headers, type='POST')
            result = x[1]['id']
        except Exception, e:
            _logger.info(_('An exception occured during the google analytics rquest: %s') % e)
            raise
        return result

    @api.model
    def update_an_experiment(self, data, google_id, website_id):
        gs_pool = self.env['google.service']
        website = self.env['website'].browse(website_id)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1]
        profileId = website.google_analytics_view_id

        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s?access_token=%s' % (accountId, webPropertyId, profileId, google_id, self.get_token())
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)

        return gs_pool._do_request(url, data_json, headers, type='PUT')

    @api.model
    def get_experiment_info(self, google_id, website_id):
        gs_pool = self.env['google.service']
        website = self.env['website'].browse(website_id)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1]
        profileId = website.google_analytics_view_id

        params = {
            'access_token': self.get_token(),
        }
        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s' % (accountId, webPropertyId, profileId, google_id)
        return gs_pool._do_request(url, params, headers, type='GET')

    @api.model
    def get_goal_info(self, website_id):
        gs_pool = self.env['google.service']
        website = self.env['website'].browse(website_id)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1]
        profileId = website.google_analytics_view_id

        params = {
            'access_token': self.get_token(),
        }
        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/goals' % (accountId, webPropertyId, profileId)
        return gs_pool._do_request(url, params, headers, type='GET')

    @api.model
    def delete_an_experiment(self, google_id, website_id):
        gs_pool = self.env['google.service']
        website = self.env['website'].browse(website_id)[0]
        webPropertyId = website.google_analytics_key
        accountId = webPropertyId.split('-')[1]
        profileId = website.google_analytics_view_id
        params = {
            'access_token': self.get_token()
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = '/analytics/v3/management/accounts/%s/webproperties/%s/profiles/%s/experiments/%s' % (accountId, webPropertyId, profileId, google_id)

        return gs_pool._do_request(url, params, headers, type='DELETE')

    @api.model
    def get_token(self):
        icp = self.env['ir.config_parameter'].sudo()
        validity = icp.get_param('google_%s_token_validity' % self.STR_SERVICE)
        token = icp.get_param('google_%s_token' % self.STR_SERVICE)
        if not (validity and token):
            raise Warning(_("You must configure your account."))
        if datetime.strptime(validity.split('.')[0], DEFAULT_SERVER_DATETIME_FORMAT) < (datetime.now() + timedelta(minutes=3)):
            token = self.do_refresh_token()
        return token

    @api.model
    def do_refresh_token(self):
        gs_pool = self.env['google.service']
        icp = self.env['ir.config_parameter'].sudo()

        rtoken = icp.get_param('google_%s_rtoken' % self.STR_SERVICE)
        all_token = gs_pool._refresh_google_token_json(rtoken, self.STR_SERVICE)

        icp.set_param('google_%s_token_validity' % self.STR_SERVICE, datetime.now() + timedelta(seconds=all_token.get('expires_in')))
        icp.set_param('google_%s_token' % self.STR_SERVICE, all_token.get('access_token'))
        return all_token.get('access_token')

    # Should be called at configuration
    def get_management_scope(self):
        return 'https://www.googleapis.com/auth/analytics https://www.googleapis.com/auth/analytics.edit'
        
    @api.model
    def authorize_google_uri(self, from_url='http://www.odoo.com', context=None):
        url = self.pool['google.service']._get_authorize_uri(self.env.cr, self.env.uid, from_url, self.STR_SERVICE, scope=self.get_management_scope(), context=self.env.context)
        return url

    # convert code from authorize into token
    @api.model
    def set_all_tokens(self, authorization_code):
        gs_pool = self.env['google.service']
        all_token = gs_pool._get_google_token_json(authorization_code, self.STR_SERVICE)
        vals = {}
        vals['google_%s_rtoken' % self.STR_SERVICE] = all_token.get('refresh_token')
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('google_%s_rtoken' % self.STR_SERVICE, all_token.get('refresh_token'))
        icp.set_param('google_%s_token_validity' % self.STR_SERVICE, datetime.now() + timedelta(seconds=all_token.get('expires_in')))
        icp.set_param('google_%s_token' % self.STR_SERVICE, all_token.get('access_token'))
