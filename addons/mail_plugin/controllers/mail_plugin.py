# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
from markupsafe import Markup
from werkzeug.exceptions import BadRequest, Forbidden

from odoo import http, tools, _
from odoo.fields import Domain
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools.image import image_data_uri
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)


class MailPluginController(http.Controller):
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
            return self._get_contact_data(partner, email)

        normalized_email = tools.email_normalize(email)
        if not normalized_email:
            return {'error': _('Bad Email.'), 'partner': {}}

        if request.env['mail.alias.domain'].sudo()._find_aliases([normalized_email]):
            return {
                'partner': {},
                'error': _('This is your notification address. Search the Contact manually to link this email to a record.'),
            }

        partner = request.env['mail.thread']._partner_find_from_emails_single([email], no_create=True)
        return self._get_contact_data(partner, email)

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
            raise BadRequest()

        partners = request.env["mail.thread"]._mail_find_partner_from_emails([email])
        partner = next((p for p in partners if p), None)

        if partner:
            return partner

        if request.env['mail.alias.domain'].sudo()._find_aliases([normalized_email]):
            raise BadRequest()

        return request.env['res.partner'].create({'name': name, 'email': email})

    @http.route('/mail_plugin/redirect_to_record/<string:model>', type='http', auth='user')
    def redirect_to_record(self, model, record_id):
        if model not in self._mail_models_access_whitelist('read'):
            raise Forbidden()

        cids = request.env.user.company_ids.ids
        request.future_response.set_cookie('cids', '-'.join(map(str, cids)))

        return request.redirect(self._get_record_redirect_url(model, record_id))

    def _get_record_redirect_url(self, model, record_id):
        return f'/odoo/{model}/{int(record_id)}'

    @http.route('/mail_plugin/search_records/<string:model>', type='jsonrpc', auth='outlook', cors='*')
    def search_records(self, model, query, limit=30):
        """Generic endpoint to search records.

        Return the records formatted for the addon,
        and the total number of records matching the search.
        """
        if model not in self._mail_models_access_whitelist('read'):
            raise Forbidden()

        if isinstance(query, str):
            terms = [query]
        else:
            terms = query
        terms = [query for query in terms if len(query) >= 3]
        if not terms:
            return [], 0

        return self._search_records(model, terms, limit)

    def _search_records(self, model, terms, limit=30):
        """Search the terms (list of valid input) on the given model.

        This method is meant to be overridden to search and format the
        records based on the model.

        :param model: The model in which to search
        :param terms: List of value to search (eg name and email for res.partner)
        :param limit: Maximum number of records to return
        """
        if model != "res.partner":
            raise Forbidden()

        alias_emails = request.env['mail.alias.domain'].sudo()._find_aliases(terms)

        domain = Domain.FALSE
        for term in terms:
            if term in alias_emails:
                continue
            domain |= (
                Domain('email_normalized', 'ilike', term)
                | Domain('complete_name', 'ilike', term)
                | Domain('ref', '=', term)
                | Domain('email', 'ilike', term)
            )

        # Search for the partner based on the email.
        # If multiple are found, take the first one.
        partners = request.env['res.partner'].search(domain, limit=limit)
        record_count = request.env['res.partner'].search_count(domain)
        return [
            self._get_partner_values(partner)
            for partner in partners
        ], record_count

    @http.route('/mail_plugin/log_mail_content', type="jsonrpc", auth="outlook", cors="*")
    def log_mail_content(
        self, model, res_id, body, email_from, email_to, email_cc,
        subject, timestamp, application_name, attachments=None):
        """Log the email on the given record.

        :param model: Model of the record on which we want to log the email
        :param res_id: ID of the record
        :param body: Raw HTML content of the email body
        :param email_from: The email address of the sender
        :param email_to: The email address of the receiver
        :param email_cc: The email CC
        :param subject: The subject of the email
        :param timestamp: The timestamp in ms
        :param application_name: The name of the application
            (will be inserted in the body)
        :param attachments: List of attachments of the email.
            List of tuple: (filename, base 64 encoded content)
        """
        allowed_model = self._mail_models_access_whitelist('write')
        if model not in allowed_model:
            _logger.error("Mail Plugin: can not log email on %s#%i (%s allowed)", model, res_id, allowed_model)
            raise Forbidden()

        if attachments:
            attachments = [
                (name, base64.b64decode(content))
                for name, content in attachments
            ]

        date = datetime.datetime.fromtimestamp(int(timestamp / 1000)).date()
        date_formated = format_date(request.env, date)
        info = Markup('<span>%s</span><br/>') % _('Sent on: %s', date_formated)
        footer = Markup('<br/><br/> %(logged_from)s <b>%(application_name)s</b> <i title="%(title)s">%(user)s</i>') % {
            'logged_from': _("Logged from"),
            'application_name': application_name,
            'title': _("%(name)s #%(id)s", name=request.env.user.name, id=request.env.user.id),
            'user': _("by %s", request.env.user.name),
        }

        request.env[model].browse(res_id).message_post(
            subject=subject,
            body=info + Markup(body) + footer,
            email_from=email_from,
            attachments=attachments,
            message_type='email',
            incoming_email_to=email_to,
            incoming_email_cc=email_cc,
        )
        return True

    @http.route('/mail_plugin/get_translations', type="jsonrpc", auth="outlook", cors="*")
    def get_translations(self):
        return self._prepare_translations()

    def _get_partner_values(self, partner):
        if not partner:
            return {}

        partner_values = {
            fname: partner[fname]
            for fname in ('id', 'name', 'email', 'phone', 'is_company')
        }
        partner_values['parent_name'] = partner.parent_name

        if partner.avatar_128:
            partner_values['image'] = image_data_uri(partner.avatar_128)
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

    def _get_contact_data(self, partner, email):
        """
        method used to return partner related values, it can be overridden by other modules if extra information have to
        be returned with the partner (e.g., leads, ...)
        """
        return {
            'partner': self._get_partner_values(partner),
            'can_create_partner': request.env['res.partner'].has_access('create'),
        }

    def _mail_models_access_whitelist(self, access):
        """Return the list of the models that the user has the given access."""
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
