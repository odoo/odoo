# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import requests
from markupsafe import Markup
from werkzeug.exceptions import Forbidden

from odoo import http, tools, _
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


class MailPluginController(http.Controller):

    @http.route('/mail_client_extension/modules/get', type="jsonrpc", auth="outlook", csrf=False, cors="*")
    def modules_get(self, **kwargs):
        """
            deprecated as of saas-14.3, not needed for newer versions of the mail plugin but necessary
            for supporting older versions
        """
        return {'modules': ['contacts', 'crm']}

    @http.route('/mail_plugin/partner/enrich_and_create_company',
                type="jsonrpc", auth="outlook", cors="*")
    def res_partner_enrich_and_create_company(self, partner_id):
        """
        Route used when the user clicks on the create and enrich partner button
        it will try to find a company using IAP, if a company is found
        the enriched company will then be created in the database
        """

        partner = request.env['res.partner'].browse(partner_id).exists()

        if not partner:
            return {'error': _("This partner does not exist")}

        if partner.parent_id:
            return {'error': _("The partner already has a company related to him")}

        normalized_email = partner.email_normalized
        if not normalized_email:
            return {'error': _('The email of this contact is not valid and we can not enrich it')}

        company, enrichment_info = self._create_company_from_iap(normalized_email)

        if company:
            partner.write({'parent_id': company.id})

        return {
            'enrichment_info': enrichment_info,
            'company': self._get_company_data(company),
        }

    @http.route('/mail_plugin/partner/enrich_and_update_company', type='jsonrpc', auth='outlook', cors='*')
    def res_partner_enrich_and_update_company(self, partner_id):
        """
        Enriches an existing company using IAP
        """
        partner = request.env['res.partner'].browse(partner_id).exists()

        if not partner:
            return {'error': _("This partner does not exist")}

        if not partner.is_company:
            return {'error': 'Contact must be a company'}

        normalized_email = partner.email_normalized
        if not normalized_email:
            return {'error': 'The email of this contact is not valid and we can not enrich it'}

        domain = tools.email_domain_extract(normalized_email)
        iap_data = self._iap_enrich(domain)

        if 'enrichment_info' in iap_data:  # means that an issue happened with the enrichment request
            return {
                'enrichment_info': iap_data['enrichment_info'],
                'company': self._get_company_data(partner),
            }

        phone_numbers = iap_data.get('phone_numbers')

        partner_values = {}

        if not partner.phone and phone_numbers:
            partner_values.update({'phone': phone_numbers[0]})

        if not partner.iap_enrich_info:
            partner_values.update({'iap_enrich_info': json.dumps(iap_data)})

        if not partner.image_128:
            logo_url = iap_data.get('logo')
            if logo_url:
                try:
                    response = requests.get(logo_url, timeout=2)
                    if response.ok:
                        partner_values.update({'image_1920': base64.b64encode(response.content)})
                except Exception:
                    pass

        model_fields_to_iap_mapping = {
            'street': 'street_name',
            'city': 'city',
            'zip': 'postal_code',
            'website': 'domain',
        }

        # only update keys for which we dont have values yet
        partner_values.update({
            model_field: iap_data.get(iap_key)
            for model_field, iap_key in model_fields_to_iap_mapping.items() if not partner[model_field]
        })

        partner.write(partner_values)

        partner.message_post_with_source(
            'iap_mail.enrich_company',
            render_values=iap_data,
            subtype_xmlid='mail.mt_note',
        )

        return {
            'enrichment_info': {'type': 'company_updated'},
            'company': self._get_company_data(partner),
        }

    @http.route(['/mail_client_extension/partner/get', '/mail_plugin/partner/get']
        , type="jsonrpc", auth="outlook", cors="*")
    def res_partner_get(self, email=None, name=None, partner_id=None, **kwargs):
        """
        returns a partner given it's id or an email and a name.
        In case the partner does not exist, we return partner having an id -1, we also look if an existing company
        matching the contact exists in the database, if none is found a new company is enriched and created automatically

        old route name "/mail_client_extension/partner/get is deprecated as of saas-14.3, it is not needed for newer
        versions of the mail plugin but necessary for supporting older versions, only the route name is deprecated not
        the entire method.
        """

        if not (partner_id or (name and email)):
            return {'error': _('You need to specify at least the partner_id or the name and the email')}

        if partner_id:
            partner = request.env['res.partner'].browse(partner_id).exists()
            return self._get_contact_data(partner)

        normalized_email = tools.email_normalize(email)
        if not normalized_email:
            return {'error': _('Bad Email.')}

        notification_emails = request.env['mail.alias.domain'].sudo().search([]).mapped('default_from_email')
        if normalized_email in notification_emails:
            return {
                'partner': {
                    'name': _('Notification'),
                    'email': normalized_email,
                    'enrichment_info': {
                        'type': 'odoo_custom_error', 'info': _('This is your notification address. Search the Contact manually to link this email to a record.'),
                    },
                },
            }

        # Search for the partner based on the email.
        # If multiple are found, take the first one.
        partner = request.env['res.partner'].search(['|', ('email', 'in', [normalized_email, email]),
                                                     ('email_normalized', '=', normalized_email)], limit=1)

        response = self._get_contact_data(partner)

        # if no partner is found in the database, we should also return an empty one having id = -1, otherwise older versions of
        # plugin won't work
        if not response['partner']:
            response['partner'] = {
                'id': -1,
                'email': email,
                'name': name,
                'enrichment_info': None,
            }
            company = self._find_existing_company(normalized_email)

            can_create_partner = request.env['res.partner'].has_access('create')

            if not company and can_create_partner:  # create and enrich company
                company, enrichment_info = self._create_company_from_iap(normalized_email)
                response['partner']['enrichment_info'] = enrichment_info
            response['partner']['company'] = self._get_company_data(company)

        return response

    @http.route('/mail_plugin/partner/search', type="jsonrpc", auth="outlook", cors="*")
    def res_partners_search(self, search_term, limit=30, **kwargs):
        """
        Used for the plugin search contact functionality where the user types a string query in order to search for
        matching contacts, the string query can either be the name of the contact, it's reference or it's email.
        We choose these fields because these are probably the most interesting fields that the user can perform a
        search on.
        The method returns an array containing the dicts of the matched contacts.
        """
        normalized_email = tools.email_normalize(search_term)

        if normalized_email:
            filter_domain = [('email_normalized', 'ilike', search_term)]
        else:
            filter_domain = ['|', '|', ('complete_name', 'ilike', search_term), ('ref', '=', search_term),
                             ('email', 'ilike', search_term)]

        # Search for the partner based on the email.
        # If multiple are found, take the first one.
        partners = request.env['res.partner'].search(filter_domain, limit=limit)

        partners = [
            self._get_partner_data(partner)
            for partner in partners
        ]
        return {"partners": partners}

    @http.route(['/mail_client_extension/partner/create', '/mail_plugin/partner/create'],
                type="jsonrpc", auth="outlook", cors="*")
    def res_partner_create(self, email, name, company):
        """
        params email: email of the new partner
        params name: name of the new partner
        params company: parent company id of the new partner
        """
        notification_emails = request.env['mail.alias.domain'].sudo().search([]).mapped('default_from_email')
        if tools.email_normalize(email) in notification_emails:
            raise Forbidden()
        # old route name "/mail_client_extension/partner/create is deprecated as of saas-14.3,it is not needed for newer
        # versions of the mail plugin but necessary for supporting older versions
        # TODO search the company again instead of relying on the one provided here?
        # Create the partner if needed.
        partner_info = {
            'name': name,
            'email': email,
        }

        #see if the partner has a parent company
        if company and company > -1:
            partner_info['parent_id'] = company
        partner = request.env['res.partner'].create(partner_info)

        response = {'id': partner.id}
        return response

    @http.route('/mail_plugin/log_mail_content', type="jsonrpc", auth="outlook", cors="*")
    def log_mail_content(self, model, res_id, message, attachments=None):
        """Log the email on the given record.

        :param model: Model of the record on which we want to log the email
        :param res_id: ID of the record
        :param message: Body of the email
        :param attachments: List of attachments of the email.
            List of tuple: (filename, base 64 encoded content)
        """
        if model not in self._mail_content_logging_models_whitelist():
            raise Forbidden()

        if attachments:
            attachments = [
                (name, base64.b64decode(content))
                for name, content in attachments
            ]

        request.env[model].browse(res_id).message_post(body=Markup(message), attachments=attachments)
        return True

    @http.route('/mail_plugin/get_translations', type="jsonrpc", auth="outlook", cors="*")
    def get_translations(self):
        return self._prepare_translations()

    def _iap_enrich(self, domain):
        """
        Returns enrichment data for a given domain, in case an error happens the response will
        contain an enrichment_info key explaining what went wrong
        """
        if domain in iap_tools._MAIL_PROVIDERS:
            # Can not enrich the provider domain names (gmail.com; outlook.com, etc)
            return {'enrichment_info': {'type': 'missing_data'}}

        enriched_data = {}
        try:
            response = request.env['iap.enrich.api']._request_enrich({domain: domain})  # The key doesn't matter
        except iap_tools.InsufficientCreditError:
            enriched_data['enrichment_info'] = {'type': 'insufficient_credit', 'info': request.env['iap.account'].get_credits_url('reveal')}
        except Exception:
            enriched_data["enrichment_info"] = {'type': 'other', 'info': 'Unknown reason'}
        else:
            enriched_data = response.get(domain)
            if not enriched_data:
                enriched_data = {'enrichment_info': {'type': 'no_data', 'info': 'The enrichment API found no data for the email provided.'}}
        return enriched_data

    def _find_existing_company(self, email):
        """Find the company corresponding to the given domain and its IAP cache.

        :param email: Email of the company we search
        :return: The partner corresponding to the company
        """
        search = self._get_iap_search_term(email)

        partner_iap = request.env["res.partner.iap"].sudo().search([("iap_search_domain", "=", search)], limit=1)
        if partner_iap:
            return partner_iap.partner_id.sudo(False)

        return request.env["res.partner"].search([("is_company", "=", True), ("email_normalized", "=ilike", "%" + search)], limit=1)

    def _get_company_data(self, company):
        if not company:
            return {'id': -1}

        try:
            company.check_access('read')
        except AccessError:
            return {'id': company.id, 'name': _('No Access')}

        fields_list = ['id', 'name', 'phone', 'email', 'website']

        company_values = dict((fname, company[fname]) for fname in fields_list)
        company_values['address'] = {'street': company.street,
                                     'city': company.city,
                                     'zip': company.zip,
                                     'country': company.country_id.name if company.country_id else ''}
        company_values['additionalInfo'] = json.loads(company.iap_enrich_info) if company.iap_enrich_info else {}
        company_values['image'] = company.image_1920

        return company_values

    def _create_company_from_iap(self, email):
        domain = tools.email_domain_extract(email)
        iap_data = self._iap_enrich(domain)
        if 'enrichment_info' in iap_data:
            return None, iap_data['enrichment_info']

        phone_numbers = iap_data.get('phone_numbers')
        emails = iap_data.get('email')
        new_company_info = {
            'is_company': True,
            'name': iap_data.get("name") or domain,
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
                _logger.warning('Download of image for new company %s failed, error %s', new_company_info['name'], e)

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

        new_company_info.update({
            'iap_search_domain': self._get_iap_search_term(email),
            'iap_enrich_info': json.dumps(iap_data),
        })

        new_company = request.env['res.partner'].create(new_company_info)

        new_company.message_post_with_source(
            'iap_mail.enrich_company',
            render_values=iap_data,
            subtype_xmlid='mail.mt_note',
        )

        return new_company, {'type': 'company_created'}

    def _get_partner_data(self, partner):

        fields_list = ['id', 'name', 'email', 'phone', 'is_company']

        partner_values = dict((fname, partner[fname]) for fname in fields_list)
        partner_values['image'] = partner.image_128
        partner_values['title'] = partner.function
        partner_values['enrichment_info'] = None

        try:
            partner.check_access('write')
            partner_values['can_write_on_partner'] = True
        except AccessError:
            partner_values['can_write_on_partner'] = False

        if not partner_values['name']:
            # Always ensure that the partner has a name
            name, email_normalized = tools.parse_contact_from_email(partner_values['email'])
            partner_values['name'] = name or email_normalized

        return partner_values

    def _get_contact_data(self, partner):
        """
        method used to return partner related values, it can be overridden by other modules if extra information have to
        be returned with the partner (e.g., leads, ...)
        """
        if partner:
            partner_response = self._get_partner_data(partner)
            if partner.company_type == 'company':
                partner_response['company'] = self._get_company_data(partner)
            elif partner.parent_id:
                partner_response['company'] = self._get_company_data(partner.parent_id)
            else:
                partner_response['company'] = self._get_company_data(None)
        else:  # no partner found
            partner_response = {}

        return {
            'partner': partner_response,
            'user_companies': request.env.user.company_ids.ids,
            'can_create_partner': request.env['res.partner'].has_access('create'),
        }

    def _mail_content_logging_models_whitelist(self):
        """
        Returns all models that emails can be logged to and that can be used by the "log_mail_content" method,
        it can be overridden by sub modules in order to whitelist more models
        """
        return ['res.partner']

    def _get_iap_search_term(self, email):
        """Return the domain or the email depending if the domain is blacklisted or not.

        So if the domain is blacklisted, we search based on the entire email address
        (e.g. asbl@gmail.com). But if the domain is not blacklisted, we search based on
        the domain (e.g. bob@sncb.be -> sncb.be)
        """
        domain = tools.email_domain_extract(email)
        return ("@" + domain) if domain not in iap_tools._MAIL_DOMAIN_BLACKLIST else email

    def _translation_modules_whitelist(self):
        """
        Returns the list of modules to be translated
        Other mail plugin modules have to override this method to include their module names
        """
        return ['mail_plugin']

    def _prepare_translations(self):
        lang = request.env['res.users'].browse(request.env.uid).lang
        translations_per_module = request.env["ir.http"]._get_translations_for_webclient(
            self._translation_modules_whitelist(), lang)[0]
        translations_dict = {}
        for module in self._translation_modules_whitelist():
            translations = translations_per_module.get(module, {})
            messages = translations.get('messages', {})
            for message in messages:
                translations_dict.update({message['id']: message['string']})
        return translations_dict
