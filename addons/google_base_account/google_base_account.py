# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from openerp.addons.web.http import request

import urllib
import urllib2
import simplejson


class google_service(osv.osv_memory):
    _name = 'google.service'

    def generate_refresh_token(self, cr, uid, service, authorization_code, context=None):
        ir_config = self.pool['ir.config_parameter']
        client_id = ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service)
        client_secret = ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_secret' % service)
        redirect_uri = ir_config.get_param(cr, SUPERUSER_ID, 'google_redirect_uri')

        #Get the Refresh Token From Google And store it in ir.config_parameter
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = dict(code=authorization_code, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, grant_type="authorization_code")
        data = urllib.urlencode(data)
        try:
            req = urllib2.Request("https://accounts.google.com/o/oauth2/token", data, headers)
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError:
            raise self.pool.get('res.config.settings').get_config_warning(cr, _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired"), context=context)

        content = simplejson.loads(content)
        return content.get('refresh_token')

    def _get_google_token_uri(self, cr, uid, service, scope, context=None):
        ir_config = self.pool['ir.config_parameter']
        params = {
            'scope': scope,
            'redirect_uri': ir_config.get_param(cr, SUPERUSER_ID, 'google_redirect_uri'),
            'client_id': ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service),
            'response_type': 'code',
            'client_id': ir_config.get_param(cr, SUPERUSER_ID, 'google_%s_client_id' % service),            
        }
        uri = 'https://accounts.google.com/o/oauth2/auth?%s' % urllib.urlencode(params)
        return uri
    
    #If no scope is passed, we use service by default to get a default scope
       
    def _get_authorize_uri(self, cr, uid, from_url, service, scope = False, context=None): #authorize_API
        if not service:
            print 'please specify a service (Calendar for example)!'
        
        state_obj = {}
        state_obj['d'] = cr.dbname
        state_obj['a'] = request and request.params.get('action') or False
        state_obj['m'] = request and request.params.get('menu_id') or False
        state_obj['s'] = service
        state_obj['from'] = from_url
                
        base_url = self.get_base_url(cr, uid, context)
        client_id = self.get_client_id(cr, uid, service, context)
                
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'state' : simplejson.dumps(state_obj),
            'scope': scope or 'https://www.googleapis.com/auth/%s' % (service,),
            'redirect_uri': base_url + '/googleauth/oauth2callback',
            'approval_prompt':'force',
            'access_type':'offline'
        }
        
        uri = self.get_uri_oauth(a='auth') + "?%s" % urllib.urlencode(params)
        return uri
            
    def _get_google_token_json(self, cr, uid, authorize_code, service, context=None): #exchange_AUTHORIZATION vs Token (service = calendar)
        res = False
        base_url = self.get_base_url(cr, uid, context)
        client_id = self.get_client_id(cr, uid, service, context)
        client_secret = self.get_client_secret(cr, uid, service, context)
                       
        params = {
            'code': authorize_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type' : 'authorization_code',
            'redirect_uri': base_url + '/googleauth/oauth2callback'
        }
                
        headers = {"content-type": "application/x-www-form-urlencoded"}
        
        try:
            data = urllib.urlencode(params)
            req = urllib2.Request(self.get_uri_oauth(a='token'), data, headers)
            content = urllib2.urlopen(req).read()
            res = simplejson.loads(content)            
            
        except urllib2.HTTPError,e:
            print e
            raise self.pool.get('res.config.settings').get_config_warning(cr, _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired"), context=context)
            
        return res
                
    def _refresh_google_token_json(self, cr, uid, refresh_token, service, context=None): #exchange_AUTHORIZATION vs Token (service = calendar)
        res = False
        base_url = self.get_base_url(cr, uid, context)
        client_id = self.get_client_id(cr, uid, service, context)
        client_secret = self.get_client_secret(cr, uid, service, context)
                       
        params = {
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type' : 'refresh_token'
        }
                
        headers = {"content-type": "application/x-www-form-urlencoded"}
        
        try:
            data = urllib.urlencode(params)
            req = urllib2.Request(self.get_uri_oauth(a='token'), data, headers)
            content = urllib2.urlopen(req).read()
            res = simplejson.loads(content)
        except urllib2.HTTPError:
            raise self.pool.get('res.config.settings').get_config_warning(cr, _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired"), context=context)
           
        return res
        
    def _do_request(self,cr,uid,uri,params={},headers={},type='POST', context=None):
        res = False
        
        print "#########################################"
        print "###  URI : %s ###" % (uri)
        print "###  HEADERS : %s ###" % (headers)
        print "###  METHOD : %s ###" % (type)
        if type=='GET':
            print "###  PARAMS : %s ###" % urllib.urlencode(params)
        else:
            print "###  PARAMS : %s ###" % (params)
        
        print "#########################################"
        
        try:
            if type.upper() == 'GET':
                data = urllib.urlencode(params)
                req = urllib2.Request(self.get_uri_api() + uri + "?" + data)#,headers)
            elif type.upper() == 'POST':
                req = urllib2.Request(self.get_uri_api() + uri, params, headers)
            else:
                raise ('Method not supported [GET or POST] not in [%s]!' % (type))
                
            content = urllib2.urlopen(req).read()
            res = simplejson.loads(content)
        except urllib2.HTTPError,e:
            print e.read()
            raise self.pool.get('res.config.settings').get_config_warning(cr, _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired"), context=context)
          
        return res
        
    def get_base_url(self, cr, uid, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url',default='http://www.openerp.com?NoBaseUrl',context=context)
        
    def get_client_id(self, cr, uid, service, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, uid, 'google_%s_client_id' % (service,),context=context)
        
    def get_client_secret(self, cr, uid, service, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, uid, 'google_%s_client_secret' % (service,),context=context)
    
    def get_uri_oauth(self,a=''): #a = optionnal action
        return "https://accounts.google.com/o/oauth2/%s" % (a,)
    
    def get_uri_api(self):
        return 'https://www.googleapis.com'
