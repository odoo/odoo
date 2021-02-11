# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import requests

from odoo import http, tools
from odoo.addons.iap.tools import iap_tools
from odoo.http import request

_logger = logging.getLogger(__name__)


class MailPluginController(http.Controller):

    def _iap_enrich(self, domain):
        enriched_data = {}
        try:
            response = request.env['iap.enrich.api']._request_enrich({domain: domain}) # The key doesn't matter
        #except odoo.addons.iap.models.iap.InsufficientCreditError as ice:
        except iap_tools.InsufficientCreditError:
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
        if domain in iap_tools._MAIL_DOMAIN_BLACKLIST:
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
