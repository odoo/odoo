# -*- coding: utf-8 -*-
import base64
from datetime import datetime, timedelta
import logging
import requests
import simplejson
import urllib2
from urlparse import urlparse, urlunparse,urljoin
import werkzeug.urls

from openerp import models, fields, api, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import Warning, AccessError

BASE_API_URL = "https://api.linkedin.com"
COMPANY_FIELDS = ["id", "name", "logo-url", "description", "industry", "website-url", "locations", "universal-name"]
PEOPLE_FIELDS = ["id", "picture-url", "public-profile-url", "first-name", "last-name", "formatted-name", "location", "phone-numbers", "im-accounts", "main-address", "headline", "positions", "summary", "specialties", "email-address"]
_logger = logging.getLogger(__name__)


class except_auth(Exception):
    """ Class for authorization exceptions """
    def __init__(self, name, value, status=None):
        Exception.__init__(self)
        self.name = name
        self.code = 401  # HTTP status code for authorization
        if status is not None:
            self.code = status
        self.args = (self.code, name, value)


class linkedin_users(models.Model):
    _inherit = 'res.users'

    linkedin_token = fields.Char(string="LinkedIn Token")
    linkedin_token_validity = fields.Datetime(string="LinkedIn Token Validity")


class web_linkedin_settings(models.TransientModel):
    _inherit = 'sale.config.settings'

    api_key = fields.Char(string="API Key", help="LinkedIn API Key")
    secret_key = fields.Char(string="Secret Key", help="LinkedIn Secret Key")
    linkedin_domain = fields.Char(string="Linkedin Domain")
    redirect_url = fields.Char(related='linkedin_domain', string="Linkedin Domain")
    linkedin_cus_sync = fields.Boolean("Show tutorial to know how to get my 'API key' and my 'Secret key'")
    company_name = fields.Char("Company", default=lambda self: self.env.user.company_id.name)

    @api.model
    def get_default_linkedin(self, fields):
        key = self.env['ir.config_parameter'].get_param("web.linkedin.apikey") or ""
        dom = self.env['ir.config_parameter'].get_param('web.base.url')
        secret_key = self.env['ir.config_parameter'].get_param('web.linkedin.secretkey')
        return {'api_key': key, 'linkedin_domain': dom + "/linkedin/authentication", 'secret_key': secret_key}

    @api.one
    def set_linkedin(self):
        config_obj = self.env['ir.config_parameter']
        apikey = self.api_key or ""
        secret_key = self.secret_key or ""
        config_obj.set_param("web.linkedin.apikey", apikey, groups=['base.group_users'])
        config_obj.set_param("web.linkedin.secretkey", secret_key, groups=['base.group_users'])

    @api.model
    def create(self, vals):
        if vals.get('api_key'):
            self.env['linkedin'].check_valid_api_key(vals.get('api_key'))
        return super(web_linkedin_settings, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('api_key'):
            self.env['linkedin'].check_valid_api_key(vals.get('api_key'))
        return  super(web_linkedin_settings, self).write(vals)


class web_linkedin_fields(models.Model):
    _inherit = 'res.partner'

    @api.model
    def linkedin_check_similar_partner(self, linkedin_datas):
        res = []
        for linkedin_data in linkedin_datas:
            partners = self.env['res.partner'].search_read(["|", ("linkedin_id", "=", linkedin_data['id']),
                    "&", ("linkedin_id", "=", False),
                    "|", ("name", "ilike", linkedin_data['firstName'] + "%" + linkedin_data['lastName']), ("name", "ilike", linkedin_data['lastName'] + "%" + linkedin_data['firstName'])], ["image", "mobile", "phone", "parent_id", "name", "email", "function", "linkedin_id"])
            if partners:
                partner = partners[0]
                if partner['linkedin_id'] and partner['linkedin_id'] != linkedin_data['id']:
                    partner.pop('id')
                if partner['parent_id']:
                    partner['parent_id'] = partner['parent_id'][0]
                for key, val in partner.items():
                    if not val:
                        partner.pop(key)
                res.append(partner)
            else:
                res.append({})
        return res

    linkedin_id = fields.Char(string="LinkedIn ID")
    linkedin_url = fields.Char(string="LinkedIn url")


class linkedin(models.AbstractModel):
    _name = 'linkedin'

    def check_valid_api_key(self, api_key):
        status = ""
        params = {
            'response_type': 'code',
            'client_id': api_key,
            'state': True,
            'redirect_uri': self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/linkedin/authentication',
        }

        url = self.get_uri_oauth(a='authorization') + "?%s" % werkzeug.url_encode(params)
        try:
            response = requests.post(url)
            response.raise_for_status()
            status = response.status_code
        except requests.exceptions.ConnectionError:
            _logger.exception("Either there is no connection or remote server is down !")
        except Exception as e:
            if status != 200:
                raise Warning(_('Something went wrong!, Please check your API Key.'))
        return True

    def sync_linkedin_contacts(self, from_url):
        """
            This method will import all first level contact from LinkedIn,
            It may raise AccessError, because user may or may not have create or write access,
            Here if user does not have one of the right from create or write then this method will allow at least for allowed operation,
            AccessError is handled as a special case, AccessError wil not raise exception instead it will return result with warning and status=AccessError.
        """
        if not self.need_authorization():
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
            params = {
                'oauth2_access_token': self.env.user.linkedin_token
            }
            connection_uri = urljoin(BASE_API_URL, "/v1/people/~/connections:(%s)" % (','.join(PEOPLE_FIELDS)))
            status, res = self.send_request(connection_uri, params=params, headers=headers, type="GET")
            return self.update_contacts(res) if not isinstance(res, str) else False
        return {'status': 'need_auth', 'url': self._get_authorize_uri(from_url=from_url, scope=True)}

    def update_contacts(self, records):
        li_records = dict((d['id'], d) for d in records.get('values', []))
        result = {'_total': len(records.get('values', [])), 'fail_warnings': [], 'status': ''}
        records_to_create, records_to_update = self.check_create_or_update(li_records)
        #Do not raise exception for AccessError, if user doesn't have one of the right from create or write
        try:
            self.create_contacts(records_to_create)
        except AccessError, e:
            result['fail_warnings'].append((e[0], str(len(records_to_create)) + " records are not created\n" + e[1]))
            result['status'] = "AccessError"
        try:
            self.write_contacts(records_to_update)
        except AccessError, e:
            result['fail_warnings'].append((e[0], str(len(records_to_update)) + " records are not updated\n" + e[1]))
            result['status'] = "AccessError"
        return result

    def check_create_or_update(self, records):
        records_to_update = {}
        records_to_create = []
        ids = records.keys()
        read_res = self.env['res.partner'].search_read([('linkedin_id', 'in', ids)], ['linkedin_id'])
        to_update = [x['linkedin_id'] for x in read_res]
        to_create = list(set(ids).difference(to_update))
        for id in to_create:
            records_to_create.append(records.get(id))
        for res in read_res:
            records_to_update[res['id']] = records.get(res['linkedin_id'])
        return records_to_create, records_to_update

    def create_contacts(self, records_to_create):
        for record in records_to_create:
            if record['id'] != 'private':
                vals = self.create_data_dict(record)
                self.env['res.partner'].create(vals)
        return True

    #Currently all fields are re-written
    def write_contacts(self, records_to_update):
        for id, record in records_to_update.iteritems():
            vals = self.create_data_dict(record)
            partner = self.env['res.partner'].search([('id', '=', id)])
            partner.write(vals)
        return True

    def create_data_dict(self, record):
        data_dict = {
            'name': record.get('formattedName', record.get("firstName", "")),
            'linkedin_url': record.get('publicProfileUrl', False),
            'linkedin_id': record.get('id', False),
        }
        #TODO: Should we add: email-address,summary
        positions = (record.get('positions') or {}).get('values', [])
        for position in positions:
            if position.get('isCurrent'):
                data_dict['function'] = position.get('title')
                company_name = False
                if position.get('company'):
                    company_name = position['company'].get('name')
                #To avoid recursion, it is quite possible that connection name and company_name is same
                #in such cases import goes fail meanwhile due to osv exception, hence skipped such connection for parent_id
                if company_name != data_dict['name']:
                    parent = self.env['res.partner'].search([('name', '=', company_name)], limit=1)
                    if parent:
                        data_dict['parent_id'] = parent.id

        image = record.get('pictureUrl') and self.url2binary(record['pictureUrl']) or False
        data_dict['image'] = image

        phone_numbers = (record.get('phoneNumbers') or {}).get('values', [])
        for phone in phone_numbers:
            if phone.get('phoneType') == 'mobile':
                data_dict['mobile'] = phone['phoneNumber']
            else:
                data_dict['phone'] = phone['phoneNumber']
        return data_dict

    def get_search_popup_data(self, offset=0, limit=5, **kw):
        """
            This method will return all needed data for LinkedIn Search Popup.
            It returns companies(including search by universal name), people, current user data and it may return warnings if any
        """
        result_data = {'warnings': []}
        companies = {}
        people = {}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
        params = {
            'oauth2_access_token': self.env.user.linkedin_token
        }

        #Profile Information of current user
        profile_uri = urljoin(BASE_API_URL, "/v1/people/~:(first-name,last-name)")
        status, res = self.with_context(kw.get('local_context') or {}).send_request(profile_uri, params=params, headers=headers, type="GET")
        result_data['current_profile'] = res

        status, companies, warnings = self.get_company_data(offset, limit, params=params, headers=headers, **kw)
        result_data['companies'] = companies
        result_data['warnings'] += warnings
        status, people, warnings = self.get_people_data(offset, limit, params=params, headers=headers, **kw)
        if status:
            result_data['people_status'] = status
        result_data['people'] = people
        result_data['warnings'] += warnings
        return result_data

    @api.model
    def get_company_data(self, offset=0, limit=5, params={}, headers={}, **kw):
        """This method will fetch company data for LinkedIn Company Search Popup
            :param offset: no of company load after show more
            :param limit: No of companies to load
            :param params: send request Param data like Access token etc
            :param headers: headers of requests
            :param kw: arguments to controller to search
            :returns: linkedin company search data, status if error and warnings
        """
        companies = {}
        universal_company = {}
        warnings = []
        if not params:
            params = {'oauth2_access_token': self.env.user.linkedin_token}
        if not headers:
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
        #search by universal-name
        if kw.get('search_uid'):
            universal_search_uri = urljoin(BASE_API_URL, "/v1/companies/universal-name=%s:(%s)" % (kw['search_uid'], ','.join(COMPANY_FIELDS)))
            status, universal_company = self.with_context(kw.get('local_context') or {}).send_request(universal_search_uri, params=params, headers=headers, type="GET")
        #Companies search
        search_params = dict(params.copy(), keywords=kw.get('search_term', "") or "", start=offset, count=limit)
        company_search_uri = urljoin(BASE_API_URL, "/v1/company-search:(companies:(%s))" % (','.join(COMPANY_FIELDS)))
        status, companies = self.with_context(kw.get('local_context') or {}).send_request(company_search_uri, params=search_params, headers=headers, type="GET")
        if companies and companies['companies'].get('values') and universal_company:
            companies['companies']['values'].append(universal_company)
        return status, companies, warnings

    @api.model
    def get_people_data(self, offset=0, limit=5, params={}, headers={}, **kw):
        """This method will fetch people data for LinkedIn people Search Popup
            :param offset: no of people load after show more
            :param limit: No of people to load
            :param params: send request Param data like Access token etc
            :param headers: headers of requests
            :param kw: arguments to controller to search
            :returns: linkedin people search data, status if error and warnings
        """
        people = {}
        public_profile = {}
        warnings = []
        if not params:
            params = {'oauth2_access_token': self.env.user.linkedin_token}
        if not headers:
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
        if kw.get('search_uid'):
            #this code may returns 400 bad request error, as per linked API doc the call is proper
            #but generated url may not have proper public url and may raise 400 or 410 status hence added a warning in response and handle warning at client side
            try:
                public_profile_url = werkzeug.url_quote_plus("http://www.linkedin.com/pub/%s" % (kw['search_uid']))
                profile_uri = urljoin(BASE_API_URL, "/v1/people/url=%s:(%s)" % (public_profile_url, ','.join(PEOPLE_FIELDS)))
                status, public_profile = self.with_context(kw.get('local_context') or {}).send_request(profile_uri, params=params, headers=headers, type="GET")

            except urllib2.HTTPError, e:
                if e.code in (400, 410):
                    warnings.append([_('LinkedIn error'), _('LinkedIn is temporary down for the searches by url.')])
                elif e.code in (401):
                    raise e
        search_params = dict(params.copy(), keywords=kw.get('search_term', "") or "", start=offset, count=limit)
        #Note: People search is allowed to only vetted API access request, please go through following link
        #https://help.linkedin.com/app/api-dvr
        people_search_uri = urljoin(BASE_API_URL, "/v1/people-search:(people:(%s))" % (','.join(PEOPLE_FIELDS)))
        status, people = self.with_context(kw.get('local_context') or {}).send_request(people_search_uri, params=search_params, headers=headers, type="GET")
        if people and people['people'].get('values') and public_profile:
            people['people']['values'].append(public_profile)
        return status, people, warnings

    @api.model
    def get_people_from_company(self, company_universalname, limit, from_url):
        if not self.need_authorization():
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'x-li-format': 'json'}
            params = {
                'oauth2_access_token': self.env.user.linkedin_token,
                'company-name': company_universalname,
                'current-company': 'true',
                'count': limit
            }
            people_criteria_uri = urljoin(BASE_API_URL, "/v1/people-search:(people:(%s))" % (','.join(PEOPLE_FIELDS)))
            status, res = self.send_request(people_criteria_uri, params=params, headers=headers, type="GET")
            return res
        else:
            return {'status': 'need_auth', 'url': self._get_authorize_uri(from_url=from_url)}

    def send_request(self, uri, params={}, headers={}, type="GET"):
        result = ""
        status = ""
        try:
            if type.upper() == "GET":
                data = werkzeug.url_encode(params)
                req = urllib2.Request(uri + "?" + data)
                for header_key, header_val in headers.iteritems():
                    req.add_header(header_key, header_val)
            elif type.upper() == 'POST':
                req = urllib2.Request(uri, params, headers)
            else:
                raise ('Method not supported [%s] not in [GET, POST]!' % (type))
            request = urllib2.urlopen(req)
            status = request.getcode()
            if int(status) in (204, 404):  # Page not found, no response
                result = {}
            else:
                content = request.read()
                result = simplejson.loads(content)
        except urllib2.HTTPError, e:
            #Should simply raise exception or simply add logger
            if e.code in (400, 410):
                raise e

            if e.code == 401:
                raise except_auth('AuthorizationError', {'url': self._get_authorize_uri(from_url=self.env.context.get('from_url'), scope=self.env.context.get('scope'))})
            #TODO: Should handle 403 for throttle limit and should display user freindly message
            status = e.code
            _logger.exception("Bad linkedin request : %s !" % e.read())
        except urllib2.URLError, e:
            _logger.exception("Either there is no connection or remote server is down !")
        return (status, result)

    def _get_authorize_uri(self, from_url, scope=False):
        """ This method return the url needed to allow this instance of OpenErp to access linkedin application """
        state_obj = dict(d=scope, f=from_url)
        config_obj = self.env['ir.config_parameter'].sudo()
        base_url = config_obj.get_param('web.base.url')
        client_id = config_obj.get_param('web.linkedin.apikey')

        params = {
            'response_type': 'code',
            'client_id': client_id,
            'state': simplejson.dumps(state_obj),
            'redirect_uri': base_url + '/linkedin/authentication',
        }

        uri = self.get_uri_oauth(a='authorization') + "?%s" % werkzeug.url_encode(params)
        return uri

    def set_all_tokens(self, token_datas):
        data = {
            'linkedin_token': token_datas.get('access_token'),
            'linkedin_token_validity': datetime.now() + timedelta(seconds=token_datas.get('expires_in'))
        }
        self.env.user.sudo().write(data)

    def need_authorization(self):
        if not self.env.user.linkedin_token_validity or \
                datetime.strptime(self.env.user.linkedin_token_validity.split('.')[0], DEFAULT_SERVER_DATETIME_FORMAT) < (datetime.now() + timedelta(minutes=1)):
            return True
        return False

    @api.model
    def test_linkedin_keys(self):
        config_obj = self.env['ir.config_parameter'].sudo()
        res = config_obj.get_param('web.linkedin.apikey') and config_obj.get_param('web.linkedin.secretkey') and True
        if res:
            return {'is_key_set': res}
        if not self.env['res.users'].has_group('base.group_system'):
            return {'show_warning': True}
        action = self.env['ir.model.data'].get_object_reference('base_setup', 'action_sale_config')[1]
        base_url = config_obj.get_param('web.base.url')
        return {'redirect_url': base_url + '/web?#action=' + str(action)}

    @api.multi
    def get_uri_oauth(self, a=''):  # a = action
        return "https://www.linkedin.com/uas/oauth2/%s" % (a,)

    @api.multi
    def url2binary(self, url):
        """Used exclusively to load images from LinkedIn profiles, must not be used for anything else."""
        _scheme, _netloc, path, params, query, fragment = urlparse(url)
        # media.linkedin.com is the master domain for LinkedIn media (replicated to CDNs),
        # so forcing it should always work and prevents abusing this method to load arbitrary URLs
        try:
            url = urlunparse(('http', 'media.licdn.com', path, params, query, fragment))
            bfile = urllib2.urlopen(url)
            return base64.b64encode(bfile.read())
        except urllib2.HTTPError, e:
            _logger.exception("Bad URl request : %s !" % e.read())
        return False
