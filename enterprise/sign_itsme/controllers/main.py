# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import sha256
from json import dumps
from urllib.parse import urlsplit
from werkzeug.urls import url_join

from odoo import http, _
from odoo.http import request
from odoo.addons.iap import jsonrpc
from odoo.tools import consteq
from odoo.addons.sign.controllers.main import Sign as SignController

IAP_DEFAULT_DOMAIN = 'https://itsme.api.odoo.com'
IAP_SERVICE_NAME = 'itsme_proxy'
class SignItsme(SignController):
    def get_document_qweb_context(self, sign_request_id, token, **post):
        res = super().get_document_qweb_context(sign_request_id, token, **post)
        if isinstance(res, dict):
            # show_thank_you_dialog and error_message come from IAP sign_itsme redirect
            res['show_thank_you_dialog'] = post.get('show_thank_you_dialog')
            res['error_message'] = post.get('error_message')
        return res

    def _validate_auth_method(self, request_item_sudo, **kwargs):
        if request_item_sudo.role_id.auth_method == 'itsme':
            referrer = request.httprequest.referrer
            if not referrer:
                return {'success': False}
            account_token = request.env['iap.account'].sudo().get(IAP_SERVICE_NAME)
            if not account_token.account_token:
                return {
                    'success': False,
                    'message': _("itsme® IAP service could not be found.")
                }
            parsed_referrer = urlsplit(referrer)
            endpoint = request.env['ir.config_parameter'].sudo().get_param('sign_itsme.iap_endpoint', IAP_DEFAULT_DOMAIN)
            itsme_credits = request.env['iap.account'].sudo().get_credits(IAP_SERVICE_NAME)
            if itsme_credits < 1:
                request_item_sudo.signed_without_extra_auth = True
                return {
                    'success': True
                }
            response = jsonrpc(url_join(endpoint, '/itsme/v1/sign_identity_request'), params={
                'account_token': account_token.account_token,
                'itsme_state': '%s.%s' % (request_item_sudo.sign_request_id.id, request_item_sudo.access_token),
                'referrer': parsed_referrer._replace(path='', query='', fragment='').geturl()
            })
            return response
        else:
            return super()._validate_auth_method(request_item_sudo, **kwargs)

    @http.route(['/itsme_sign/itsme_successful'], type='json', auth='public', csrf='false')
    def sign_itsme_complete(self, itsme_state, name, birthdate, itsme_hash):
        if not itsme_state:
            return {
                'success': False,
            }
        sign_request_id, token = itsme_state.split(".")
        request_item = request.env['sign.request.item'].sudo().search([
            ('sign_request_id', '=', int(sign_request_id)),
            ('access_token', '=', token),
            ('state', '=', 'sent')
        ], limit=1)
        # check that values are correct (to prevent users from abusing this route to validate itsme documents without having gone through the itsme validation)
        if not (request_item and itsme_hash and request_item.role_id.auth_method == 'itsme'):
            return {
                'success': False
            }

        values = {
            'name': name,
            'birthdate': birthdate
        }
        computed_hash_from_values = sha256(dumps(values, sort_keys=True, ensure_ascii=True, indent=None).encode('utf-8')).hexdigest()
        if not consteq(computed_hash_from_values, itsme_hash):
            return {
                'success': False
            }

        sign_user = request.env['res.users'].sudo().search([('partner_id', '=', request_item.partner_id.id)], limit=1)
        if sign_user:
            # sign as a known user
            request_item = request_item.with_user(sign_user).sudo()

        request_item.write_itsme_data(itsme_hash, name, birthdate)
        request_item._post_fill_request_item()
        return {
            'success': True
        }

    @http.route(['/itsme/has_itsme_credits'], type="json", auth="public")
    def has_itsme_credits(self):
        return request.env['iap.account'].sudo().get_credits(IAP_SERVICE_NAME) >= 1

    def get_iap_credit_warnings(self):
        warnings = super().get_iap_credit_warnings()
        roles_with_itsme = request.env['sign.item.role'].sudo().search([('auth_method', '=', 'itsme')])
        if roles_with_itsme:
            if self.has_warning_for_service(roles_with_itsme, IAP_SERVICE_NAME):
                warnings.append({
                    'auth_method': 'itsme®',
                    'iap_url': request.env['iap.account'].sudo().get_credits_url(service_name=IAP_SERVICE_NAME),
                })
        return warnings
