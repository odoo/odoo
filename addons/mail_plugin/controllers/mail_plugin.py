# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
from markupsafe import Markup
from werkzeug.exceptions import Forbidden

from odoo import http, tools, _
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

    @http.route('/mail_plugin/partner/get', type="jsonrpc", auth="outlook", cors="*")
    def res_partner_get(self, email=None, partner_id=None, **kwargs):
        """
        returns a partner given its id or an email.
        In case the partner does not exist, we return partner having an id -1, we also look if an existing company
        matching the contact exists in the database, if none is found a new company is enriched and created automatically
        """
        if not partner_id and not email:
            return {'error': _('You need to specify at least the partner_id or the email')}

        if partner_id:
            partner = request.env['res.partner'].browse(partner_id).exists()
            return self._get_contact_data(partner)

        normalized_email = tools.email_normalize(email)
        if not normalized_email:
            return {'error': _('Bad Email.'), 'partner': {}}

        notification_emails = request.env['mail.alias.domain'].sudo().search([]).mapped('default_from_email')
        if normalized_email in notification_emails:
            return {
                'partner': {},
                'error': _('This is your notification address. Search the Contact manually to link this email to a record.'),
            }

        # Search for the partner based on the email.
        # If multiple are found, take the first one.
        partner = request.env['res.partner'].search(['|', ('email', 'in', [normalized_email, email]),
                                                     ('email_normalized', '=', normalized_email)], limit=1)

        return self._get_contact_data(partner)

    @http.route('/mail_plugin/partner/create', type="jsonrpc", auth="outlook", cors="*")
    def res_partner_create(self, email, name):
        """Create the partner with the given email and name.

        :param email: email of the new partner
        :param name: name of the new partner
        """
        partner = self._search_or_create_partner(email, name)
        return self._get_partner_values(partner)

    def _search_or_create_partner(self, email, name):
        normalized_email = tools.email_normalize(email)
        if not normalized_email:
            raise Forbidden()

        partners = request.env["mail.thread"]._mail_find_partner_from_emails([email])
        partner = next((p for p in partners if p), None)

        if partner:
            return partner

        notification_emails = request.env['mail.alias.domain'].sudo().search([]).mapped('default_from_email')
        if normalized_email in notification_emails:
            raise Forbidden()

        return request.env['res.partner'].create({'name': name, 'email': email})

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
        company_values['image'] = company.image_1920

        return company_values

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
            if partner.is_company:
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
