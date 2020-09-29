# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import datetime
import hmac
import json
import logging
import odoo
import requests
import werkzeug

import odoo.addons.iap.tools.iap_tools
from odoo import http, tools
from odoo.http import request
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)

# The top 100 email providers as I'm writing this comment.
# We don't want to attempt matching companies in the database based on those domains, or we will end up with multiple
# and/or the wrong company. This solution won't work all the time, the goal is to cover most cases.
_DOMAIN_BLACKLIST = {'gmail.com', 'yahoo.com', 'hotmail.com', 'aol.com', 'hotmail.co.uk', 'hotmail.fr', 'msn.com',
                     'yahoo.fr', 'wanadoo.fr', 'orange.fr', 'comcast.net', 'yahoo.co.uk', 'yahoo.com.br', 'yahoo.co.in',
                     'live.com', 'rediffmail.com', 'free.fr', 'gmx.de', 'web.de', 'yandex.ru', 'ymail.com', 'libero.it',
                     'outlook.com', 'uol.com.br', 'bol.com.br', 'mail.ru', 'cox.net', 'hotmail.it', 'sbcglobal.net',
                     'sfr.fr', 'live.fr', 'verizon.net', 'live.co.uk', 'googlemail.com', 'yahoo.es', 'ig.com.br',
                     'live.nl', 'bigpond.com', 'terra.com.br', 'yahoo.it', 'neuf.fr', 'yahoo.de', 'alice.it',
                     'rocketmail.com', 'att.net', 'laposte.net', 'facebook.com', 'bellsouth.net', 'yahoo.in',
                     'hotmail.es', 'charter.net', 'yahoo.ca', 'yahoo.com.au', 'rambler.ru', 'hotmail.de', 'tiscali.it',
                     'shaw.ca', 'yahoo.co.jp', 'sky.com', 'earthlink.net', 'optonline.net', 'freenet.de', 't-online.de',
                     'aliceadsl.fr', 'virgilio.it', 'home.nl', 'qq.com', 'telenet.be', 'me.com', 'yahoo.com.ar',
                     'tiscali.co.uk', 'yahoo.com.mx', 'voila.fr', 'gmx.net', 'mail.com', 'planet.nl', 'tin.it',
                     'live.it', 'ntlworld.com', 'arcor.de', 'yahoo.co.id', 'frontiernet.net', 'hetnet.nl',
                     'live.com.au', 'yahoo.com.sg', 'zonnet.nl', 'club-internet.fr', 'juno.com', 'optusnet.com.au',
                     'blueyonder.co.uk', 'bluewin.ch', 'skynet.be', 'sympatico.ca', 'windstream.net', 'mac.com',
                     'centurytel.net', 'chello.nl', 'live.ca', 'aim.com', 'bigpond.net.au'}


class MailClientExtensionController(http.Controller):

    @http.route('/mail_client_extension/auth', type='http', auth="user", methods=['GET'], website=True)
    def auth(self, **values):
        """
         Once authenticated this route renders the view that shows an app wants to access Odoo.
         The user is invited to allow or deny the app. The form posts to `/mail_client_extension/auth/confirm`.
         """
        return request.render('mail_client_extension.app_auth', values)

    @http.route('/mail_client_extension/auth/confirm', type='http', auth="user", methods=['POST'])
    def auth_confirm(self, scope, friendlyname, redirect, info=None, do=None, **kw):
        """
        Called by the `app_auth` template. If the user decided to allow the app to access Odoo, a temporary auth code
        is generated and he is redirected to `redirect` with this code in the URL. It should redirect to the app, and
        the app should then exchange this auth code for an access token by calling
        `/mail_client_extension/auth/access_token`.
        """
        parsed_redirect = werkzeug.urls.url_parse(redirect)
        params = parsed_redirect.decode_query()
        if do:
            name = friendlyname if not info else f'{friendlyname}: {info}'
            auth_code = self._generate_auth_code(scope, name)
            # params is a MultiDict which does not support .update() with kwargs
            params.update({'success': 1, 'auth_code': auth_code})
        else:
            params['success'] = 0
        updated_redirect = parsed_redirect.replace(query=werkzeug.urls.url_encode(params))
        return werkzeug.utils.redirect(updated_redirect.to_url())

    # In this case, an exception will be thrown in case of preflight request if only POST is allowed.
    @http.route('/mail_client_extension/auth/access_token', type='json', auth="none", cors="*", methods=['POST', 'OPTIONS'])
    def auth_access_token(self, auth_code, **kw):
        """
        Called by the external app to exchange an auth code, which is temporary and was passed in a URL, for an
        access token, which is permanent, and can be used in the `Authorization` header to authorize subsequent requests
        """
        auth_message = self._get_auth_code_data(auth_code)
        if not auth_message:
            return {"error": "Invalid code"}
        request.uid = auth_message['uid']
        scope = 'odoo.plugin.' + auth_message.get('scope', '')
        api_key = request.env['res.users.apikeys']._generate(scope, auth_message['name'])
        return {'access_token': api_key }

    def _get_auth_code_data(self, auth_code):
        data, auth_code_signature = auth_code.split('.')
        data = base64.b64decode(data)
        auth_code_signature = base64.b64decode(auth_code_signature)
        signature = odoo.tools.misc.hmac(request.env(su=True), 'mail_client_extension', data).encode()
        if not hmac.compare_digest(auth_code_signature, signature):
            return None

        auth_message = json.loads(data)
        # Check the expiration
        if datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(auth_message['timestamp']) > datetime.timedelta(minutes=3):
            return None

        return auth_message

    # Using UTC explicitly in case of a distributed system where the generation and the signature verification do not
    # necessarily happen on the same server
    def _generate_auth_code(self, scope, name):
        auth_dict = {
            'scope': scope,
            'name': name,
            'timestamp': int(datetime.datetime.utcnow().timestamp()),  # <- elapsed time should be < 3 mins when verifying
            'uid': request.uid,
        }
        auth_message = json.dumps(auth_dict, sort_keys=True).encode()
        signature = odoo.tools.misc.hmac(request.env(su=True), 'mail_client_extension', auth_message).encode()
        auth_code = "%s.%s" % (base64.b64encode(auth_message).decode(), base64.b64encode(signature).decode())
        _logger.info('Auth code created - user %s, scope %s', request.env.user, scope)
        return auth_code

    def _iap_enrich(self, domain):
        enriched_data = {}
        try:
            response = request.env['iap.enrich.api']._request_enrich({domain: domain}) # The key doesn't matter
        #except odoo.addons.iap.models.iap.InsufficientCreditError as ice:
        except odoo.addons.iap.tools.iap_tools.InsufficientCreditError:
            enriched_data['enrichment_info'] = {'type': 'insufficient_credit', 'info': request.env['iap.account'].get_credits_url('reveal')}
        except Exception as e:
            enriched_data["enrichment_info"] = {'type': 'other', 'info': 'Unknown reason'}
        else:
            enriched_data = response.get(domain)
            if not enriched_data:
                enriched_data = {'enrichment_info': {'type': 'no_data', 'info': 'The enrichment API found no data for the email provided.'}}
        return enriched_data

    @http.route('/mail_client_extension/modules/get', type="json", auth="outlook", csrf=False, cors="*")
    def modules_get(self,  **kwargs):
        return {'modules': ['contacts', 'crm']}

    # Find an existing company based on the email.
    def _find_existing_company(self, domain):
        if domain in _DOMAIN_BLACKLIST:
            return
        return request.env['res.partner'].search([('is_company', '=', True), ('email', '=ilike', '%' + domain)], limit=1)

    def _get_company_dict(self, company):
        if not company:
            return {'id': -1}

        return {
                    'id': company.id,
                    'name': company.name,
                    'phone': company.phone,
                    'mobile': company.mobile,
                    'email': company.email,
                    'address': {
                        'street': company.street,
                        'city': company.city,
                        'zip': company.zip,
                        'country': company.country_id.name if company.country_id else ''
                    },
                    'website': company.website,
                    'additionalInfo': json.loads(company.iap_enrich_info) if company.iap_enrich_info else {}
                }

    def _create_company_from_iap(self, domain):
        iap_data = self._iap_enrich(domain)
        if 'enrichment_info' in iap_data:
            return None, iap_data['enrichment_info']

        phone_numbers = iap_data.get('phone_numbers')
        emails = iap_data.get('email')
        new_company_info = {
            'is_company': True,
            'name': iap_data.get("name"),
            'street': iap_data.get("street_name"),
            'city': iap_data.get("city"),
            'zip': iap_data.get("postal_code"),
            'phone': phone_numbers[0] if phone_numbers else None,
            'website': iap_data.get("domain"),
            'email': emails[0] if emails else None
        }

        logo_url = iap_data.get('logo')
        if logo_url:
            try:
                response = requests.get(logo_url, timeout=2)
                if response.ok:
                    new_company_info['image_1920'] = base64.b64encode(response.content)
            except Exception as e:
                _logger.warning('Download of image for new company %r failed, error %r' % (new_company_info.name, e))

        if iap_data.get('country_code'):
            country = request.env['res.country'].search([('code', '=', iap_data['country_code'].upper())])
            if country:
                new_company_info['country_id'] = country.id
                if iap_data.get('state_code'):
                    state = request.env['res.country.state'].search([
                    ('code', '=', iap_data['state_code']),
                    ('country_id', '=', country.id)
                    ])
                    if state:
                        new_company_info['state_id'] = state.id

        new_company_info['iap_enrich_info'] = json.dumps(iap_data)
        new_company = request.env['res.partner'].create(new_company_info)
        new_company.message_post_with_view(
            'iap_mail.enrich_company',
            values=iap_data,
            subtype_id=request.env.ref('mail.mt_note').id,
        )
        
        return new_company, {'type': 'company_created'}

    @http.route('/mail_client_extension/partner/get', type="json", auth="outlook", cors="*")
    def res_partner_get_by_email(self, email, name, **kwargs):
        response = {}

        #compute the sender's domain
        normalized_email = tools.email_normalize(email)
        if not normalized_email:
            response['error'] = 'Bad email.'
            return response
        sender_domain = normalized_email.split('@')[1]

        # Search for the partner based on the email.
        # If multiple are found, take the first one.
        partner = request.env['res.partner'].search([('email', 'in', [normalized_email, email])], limit=1)
        if partner:
            response['partner'] = {
                'id': partner.id,
                'name': partner.name,
                'title': partner.function,
                'email': partner.email,
                'image': partner.image_128,
                'phone': partner.phone,
                'mobile': partner.mobile,
                'enrichment_info': None
            }
            # if there is already a company for this partner, just take it without enrichment.
            if partner.parent_id:
                response['partner']['company'] = self._get_company_dict(partner.parent_id)
            else:
                company = self._find_existing_company(sender_domain)
                if not company: # create and enrich company
                    company, enrichment_info = self._create_company_from_iap(sender_domain)
                    response['enrichment_info'] = enrichment_info
                partner.write({'parent_id': company})
                response['partner']['company'] = self._get_company_dict(company)
        else: #no partner found
            response['partner'] = {
                'id': -1,
                'name': name,
                'email': email,
                'enrichment_info': None
            }
            company = self._find_existing_company(sender_domain)
            if not company:  # create and enrich company
                company, enrichment_info = self._create_company_from_iap(sender_domain)
                response['enrichment_info'] = enrichment_info
            response['partner']['company'] = self._get_company_dict(company)

        return response

    @http.route('/mail_client_extension/partner/create', type="json", auth="outlook", cors="*")
    def res_partner_create(self, email, name, company, **kwargs):
        # TODO search the company again instead of relying on the one provided here?
        # Create the partner if needed.
        partner_info = {
            'name': name,
            'email': email,
        }
        if company > -1:
            partner_info['parent_id'] = company
        partner = request.env['res.partner'].create(partner_info)

        response = {'id': partner.id}
        return response

    @http.route('/mail_client_extension/log_single_mail_content', type="json", auth="outlook", cors="*")
    def log_single_mail_content(self, lead, message, **kw):
        crm_lead = request.env['crm.lead'].browse(lead)
        crm_lead.message_post(body=message)

    @http.route('/mail_client_extension/lead/get_by_partner_id', type="json", auth="outlook", cors="*")
    def crm_lead_get_by_partner_id(self, partner, limit, offset, **kwargs):
        partner_leads = request.env['crm.lead'].search([('partner_id', '=', partner)], offset=offset, limit=limit)
        leads = []
        for lead in partner_leads:
            leads.append({
                'id': lead.id,
                'name': lead.name,
                'expected_revenue': formatLang(request.env, lead.expected_revenue, monetary=True, currency_obj=lead.company_currency),
            })

        return {'leads': leads}

    @http.route('/mail_client_extension/lead/create_from_partner', type='http', auth='user', methods=['GET'])
    def crm_lead_redirect_form_view(self, partner_id):
        server_action = http.request.env.ref("mail_client_extension.lead_creation_prefilled_action")
        return werkzeug.utils.redirect('/web#action=%s&model=crm.lead&partner_id=%s' % (server_action.id, int(partner_id)))
