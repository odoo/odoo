# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import requests
from werkzeug.exceptions import Forbidden

from odoo import http, tools, _
from odoo.addons.iap.tools import iap_tools
from odoo.http import request

_logger = logging.getLogger(__name__)


class MailPluginController(http.Controller):

    @http.route('/mail_client_extension/modules/get', type="json", auth="outlook", csrf=False, cors="*")
    def modules_get(self, **kwargs):
        """
            deprecated as of saas-14.3, not needed for newer versions of the mail plugin but necessary
            for supporting older versions
        """
        return {'modules': ['contacts', 'crm']}

    @http.route('/mail_plugin/partner/enrich_and_create_company',
                type="json", auth="outlook", cors="*")
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
            return {'error': _('Contact has no valid email')}

        company, enrichment_info = request.env['res.partner']._create_from_iap_enrich(normalized_email)
        if company:
            partner.write({'parent_id': company})

        return {
            'enrichment_info': enrichment_info,
            'company': self._get_company_data(company),
        }

    @http.route('/mail_plugin/partner/enrich_and_update_company', type='json', auth='outlook', cors='*')
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
            return {'error': 'Contact has no valid email'}

        enrichment_info = partner._update_from_iap_enrich()
        if enrichment_info:
            return None, enrichment_info

        return {
            'enrichment_info': {'type': 'company_updated'},
            'company': self._get_company_data(partner),
        }

    @http.route(['/mail_client_extension/partner/get', '/mail_plugin/partner/get'],
                type="json", auth="outlook", cors="*")
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
            partner = request.env['res.partner'].browse(partner_id)
            return self._get_contact_data(partner)

        normalized_email = tools.email_normalize(email)
        if not normalized_email:
            return {'error': _('Bad Email.')}

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
            company, enrichment_info = request.env['res.partner']._fetch_from_iap_enrich(normalized_email)
            if enrichment_info:  # create and enrich company
                response['partner']['enrichment_info'] = enrichment_info
            response['partner']['company'] = self._get_company_data(company)

        return response

    @http.route('/mail_plugin/partner/search', type="json", auth="outlook", cors="*")
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
            filter_domain = [('email_normalized', '=', search_term)]
        else:
            filter_domain = ['|', '|', ('display_name', 'ilike', search_term), ('ref', '=', search_term),
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
                type="json", auth="outlook", cors="*")
    def res_partner_create(self, email, name, company):
        """
        params email: email of the new partner
        params name: name of the new partner
        params company: parent company id of the new partner
        """
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

    @http.route('/mail_plugin/log_mail_content', type="json", auth="outlook", cors="*")
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

        request.env[model].browse(res_id).message_post(body=message, attachments=attachments)
        return True

    @http.route('/mail_plugin/get_translations', type="json", auth="outlook", cors="*")
    def get_translations(self):
        return self._prepare_translations()

    def _get_company_data(self, company):
        if not company:
            return {'id': -1}

        fields_list = ['id', 'name', 'phone', 'mobile', 'email', 'website']

        company_values = dict((fname, company[fname]) for fname in fields_list)
        company_values['address'] = {'street': company.street,
                                     'city': company.city,
                                     'zip': company.zip,
                                     'country': company.country_id.name if company.country_id else ''}
        company_values['additionalInfo'] = json.loads(company.iap_enrich_info) if company.iap_enrich_info else {}
        company_values['image'] = company.image_1920

        return company_values

    def _get_partner_data(self, partner):
        fields_list = ['id', 'name', 'email', 'phone', 'mobile', 'is_company']

        partner_values = dict((fname, partner[fname]) for fname in fields_list)
        partner_values['image'] = partner.image_128
        partner_values['title'] = partner.function
        partner_values['enrichment_info'] = None

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
            'user_companies': request.env['res.users'].browse(request.uid).company_ids.ids
        }

    def _mail_content_logging_models_whitelist(self):
        """
        Returns all models that emails can be logged to and that can be used by the "log_mail_content" method,
        it can be overridden by sub modules in order to whitelist more models
        """
        return ['res.partner']

    def _translation_modules_whitelist(self):
        """
        Returns the list of modules to be translated
        Other mail plugin modules have to override this method to include their module names
        """
        return ['mail_plugin']

    def _prepare_translations(self):
        lang = request.env['res.users'].browse(request.uid).lang
        translations_per_module = request.env["ir.translation"].get_translations_for_webclient(
            self._translation_modules_whitelist(), lang)[0]
        translations_dict = {}
        for module in self._translation_modules_whitelist():
            translations = translations_per_module.get(module, {})
            messages = translations.get('messages', {})
            for message in messages:
                translations_dict.update({message['id']: message['string']})
        return translations_dict
