# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import pytz
import ipaddress
import json
import requests
import socket
import hmac
from hashlib import sha256
from werkzeug import urls

from odoo import api, models, _
from odoo.http import request
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SANDBOX_API_URL = 'https://test-api.service.hmrc.gov.uk'
PRODUCTION_API_URL = 'https://api.service.hmrc.gov.uk'
TIMEOUT = 10


class HmrcService(models.AbstractModel):
    """
    Service in order to pass through our authentication proxy
    """
    _name = 'hmrc.service'
    _description = 'HMRC service'

    @api.model
    def _login(self):
        """
        Checks if there is a userlogin (proxy) or a refresh of the tokens needed and ask for new ones
        If needed, it returns the url action to log in with HMRC
        Raise when something unexpected happens (enterprise contract not valid e.g.)
        :return: False when no login through hmrc needed by the user, otherwise the url action
        """
        user = self.env.user
        login_needed = False
        if user.l10n_uk_user_token:
            if not user.l10n_uk_hmrc_vat_token or user.l10n_uk_hmrc_vat_token_expiration_time < datetime.now() + timedelta(minutes=1):
                try:
                    url = self._get_proxy_server() + '/onlinesync/l10n_uk/get_tokens'
                    dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
                    data = json.dumps({'params': {'user_token': self.env.user.l10n_uk_user_token, 'dbuuid': dbuuid}})
                    resp = requests.request('GET', url, data=data,
                                            headers={'content-type': "application/json"}, timeout=TIMEOUT) #json-rpc
                    resp.raise_for_status()
                    response = resp.json()
                    response = response.get('result', {})
                    self._write_tokens(response)
                except:
                    # If it is a connection error, don't delete credentials and re-raise
                    raise
                else: #In case no error was thrown, but an error is indicated
                    if response.get('error'):
                        self._clean_tokens()
                        self._cr.commit() # Even with the raise, we want to commit the cleaning of the tokens in the db
                        raise UserError(_(
                            'There was a problem refreshing the tokens.  Please log in again. %(error)s',
                            error=response.get('message'),
                        ))
                    else:
                        # Let the user know they established the connection and can submit the report.
                        self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                            'type': 'success',
                            'message': _("You are successfully connected to HMRC. You can now send the VAT report."),
                        })
        else:
            # if no user_token, ask for one
            url = self._get_proxy_server() + '/onlinesync/l10n_uk/get_user'
            dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
            data = json.dumps({'params': {'dbuuid': dbuuid}})
            resp = requests.request('POST', url, data=data, headers={'content-type': 'application/json', 'Accept': 'text/plain'})
            resp.raise_for_status()
            contents = resp.json()
            contents = contents.get('result')
            if contents.get('error'):
                raise UserError(contents.get('message'))
            user.sudo().write({'l10n_uk_user_token': contents.get('user_token')})
            login_needed = True

        if login_needed:
            url = self.env['hmrc.service']._get_oauth_url(user.l10n_uk_user_token)
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'self',
            }
        return False

    @api.model
    def _get_fraud_prevention_info(self, client_data=None):
        """
        https://developer.service.hmrc.gov.uk/api-documentation/docs/fraud-prevention
        """
        gov_dict = {}
        try:
            environ = request.httprequest.environ
            headers = request.httprequest.headers
            remote_address = request.httprequest.remote_addr
            remote_needed = not ipaddress.ip_address(remote_address).is_private
            hostname = request.httprequest.host.split(":")[0]
            server_public_ip = socket.gethostbyname(hostname)
            public_ip_needed = not ipaddress.ip_address(server_public_ip).is_private
            tz = self.env.context.get('tz')
            if tz:
                tz_hour = datetime.now(pytz.timezone(tz)).strftime('%z')
                utc_offset = 'UTC' + tz_hour[:3] + ':' + tz_hour[-2:]
            else:
                utc_offset = 'UTC+00:00'

            ICP = self.env['ir.config_parameter'].sudo()
            enterprise_code = ICP.get_param('database.enterprise_code')
            db_secret = ICP.get_param('database.secret')
            if enterprise_code:
                hashed_license = hmac.new(enterprise_code.encode(),
                                          db_secret.encode(),
                                          sha256).hexdigest()
            else:
                hashed_license = ''
            gov_vendor_version = self.sudo().env.ref('base.module_base').latest_version

            gov_dict['Gov-Client-Connection-Method'] = 'WEB_APP_VIA_SERVER'
            if remote_needed: #no need when on a private network
                gov_dict['Gov-Client-Public-IP'] = urls.url_quote(remote_address)
                gov_dict['Gov-Client-Public-Port'] = urls.url_quote(str(environ.get('REMOTE_PORT')))
            if 'totp_enabled' in self.env.user._fields and self.env.user.totp_enabled:
                # We can not percent encode the separator, so we have to split the string as such to percent encode each key and value
                gov_dict['Gov-Client-Multi-Factor'] = "{}={type}&{}={time}&{}={unique}".format(
                    urls.url_quote('type'),
                    urls.url_quote('timestamp'),
                    urls.url_quote('unique-reference'),
                    type=urls.url_quote('TOTP'),
                    time=urls.url_quote(datetime.utcnow().isoformat(timespec='milliseconds')+'Z', unsafe=':'),  # We need to specify to percent encode ':'
                    unique=urls.url_quote(self.env.user._l10n_uk_hmrc_unique_reference()))
            gov_dict['Gov-Client-Timezone'] = utc_offset
            gov_dict['Gov-Client-Browser-JS-User-Agent'] = (environ.get('HTTP_USER_AGENT'))
            gov_dict['Gov-Vendor-Version'] = '&'.join([urls.url_quote("Odoo") + "=" + urls.url_quote(gov_vendor_version)]*2) # We can not percent encode the separator and we need to do it for the key and the value. Client and Server sides are the same
            gov_dict['Gov-Client-User-IDs'] = urls.url_quote("Odoo") + "=" + urls.url_quote(self.env.user.name)  # We can not percent encode the separator, same as Gov-Vendor-Version
            gov_dict['Gov-Client-Browser-Do-Not-Track'] = 'true' if headers.get('DNT') == '1' else 'false'
            gov_dict['Gov-Client-Screens'] = f"width={client_data['screen_width']}&height={client_data['screen_height']}&scaling-factor={client_data['screen_scaling_factor']}&colour-depth={client_data['screen_color_depth']}" if client_data else ''
            gov_dict['Gov-Client-Window-Size'] = f"width={client_data['window_width']}&height={client_data['window_height']}" if client_data else ''
            gov_dict['Gov-Client-Public-Ip-Timestamp'] = datetime.utcnow().isoformat(timespec='milliseconds')+'Z'
            gov_dict['Gov-Vendor-Product-Name'] = urls.url_quote("Odoo")
            gov_dict['Gov-Client-Device-Id'] = client_data['hmrc_gov_client_device_id'] if client_data else ''
            gov_dict['Gov-Vendor-Forwarded'] = f"by={server_public_ip}&for={remote_address}"
            if public_ip_needed: # No need when on a private network
                gov_dict['Gov-Vendor-Public-IP'] = server_public_ip
            if hashed_license:
                gov_dict['Gov-Vendor-License-IDs'] = urls.url_quote("Odoo") + "=" + urls.url_quote(hashed_license)
        except Exception:
            _logger.warning("Could not construct fraud prevention headers", exc_info=True)
        return gov_dict

    @api.model
    def _write_tokens(self, tokens):
        vals = {}
        vals['l10n_uk_hmrc_vat_token_expiration_time'] = tokens.get('expiration_time')
        vals['l10n_uk_hmrc_vat_token'] = tokens.get('access_token')
        self.env.user.sudo().write(vals)

    @api.model
    def _clean_tokens(self):
        vals = {}
        vals['l10n_uk_user_token'] = ''
        vals['l10n_uk_hmrc_vat_token_expiration_time'] = False
        vals['l10n_uk_hmrc_vat_token'] = ''
        self.env.user.sudo().write(vals)

    def _get_local_hmrc_oauth_url(self):
        """ The user will be redirected to this url after accepting (or not) permission grant.
        """
        return self._get_proxy_server() + '/onlinesync/l10n_uk/hmrc'

    @api.model
    def _get_state(self, userlogin):
        action = self.env.ref('account_reports.action_account_report_gt')
        # Search your own host
        url = request.httprequest.scheme + '://' + request.httprequest.host
        return json.dumps({
            'url': url,
            'user': userlogin,
            'action': action.id,
        })

    @api.model
    def _get_oauth_url(self, login):
        """ Generates the url to hmrc oauth endpoint.
        """
        oauth_url = self._get_endpoint_url('/oauth/authorize')
        url_params = {
            'response_type': 'code',
            'client_id': self._get_hmrc_client_id(),
            'scope': 'read:vat write:vat',
            'state': self._get_state(login),
            'redirect_uri': self._get_local_hmrc_oauth_url(),
        }
        return oauth_url + '?' + urls.url_encode(url_params)

    @api.model
    def _get_endpoint_url(self, endpoint):
        mode = self.env['ir.config_parameter'].sudo().get_param("l10n_uk_reports.hmrc_mode", 'production')
        base_url = PRODUCTION_API_URL if mode == 'production' else SANDBOX_API_URL
        return base_url + endpoint

    @api.model
    def _get_proxy_server(self):
        mode = self.env['ir.config_parameter'].sudo().get_param("l10n_uk_reports.hmrc_mode", 'production')
        proxy_server = 'https://l10n-uk-hmrc.api.odoo.com' if mode == 'production' else 'https://l10n-uk-hmrc.test.odoo.com'
        return proxy_server

    @api.model
    def _get_hmrc_client_id(self):
        mode = self.env['ir.config_parameter'].sudo().get_param("l10n_uk_reports.hmrc_mode", 'production')
        hmrc_client_id = 'GqJgi8Hal1hsEwbG6rY6i9Ag1qUa' if mode == 'production' else 'dTdANDSeX4fiw63DicmUaAVQDSMa'
        return hmrc_client_id
