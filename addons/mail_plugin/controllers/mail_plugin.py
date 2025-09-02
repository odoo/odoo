# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
from markupsafe import Markup
from werkzeug.exceptions import Forbidden

from odoo import http, tools, _
from odoo.fields import Domain
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools.image import image_data_uri

_logger = logging.getLogger(__name__)


class MailPluginController(http.Controller):

    @http.route('/mail_plugin/activity/get', type='jsonrpc', auth='outlook', cors='*')
    def mail_activity_get(self):
        """Get the activities linked to the current user."""
        today = datetime.date.today()
        activities = request.env['mail.activity'].search(
            [
                ('user_id', '=', request.env.user.id),
                ('date_deadline', '<', today + datetime.timedelta(days=7)),
            ],
            order='date_deadline DESC',
            limit=100,
        )

        def _date_to_string(date):
            # See `ActivityListPopoverItem@delayLabel`
            diff = date - today
            if diff == datetime.timedelta():
                return _('Today')
            if diff == datetime.timedelta(days=-1):
                return _('Yesterday')
            if diff < datetime.timedelta(days=-1):
                return _('%s days overdue', abs(diff.days))
            if diff == datetime.timedelta(days=1):
                return _('Tomorrow')
            return _('Due in %s days', diff.days)

        def _activity_to_json(activity):
            return {
                'id': activity.id,
                'summary': activity.summary or activity.activity_type_id.name or _('Activity'),
                'date_deadline_str': _date_to_string(activity.date_deadline),
                'date_deadline_timestamp': int(activity.date_deadline.strftime("%s")),
                'res_name': activity.res_name,
                'res_id': activity.res_id,
                'res_model': activity.res_model,
            }

        groups = [
            [_('Late'), []],
            [_('Today'), []],
            [_('Tomorrow'), []],
            [_('Next Week'), []],
        ]

        for activity in activities:
            if activity.date_deadline < today:
                groups[0][1].append(_activity_to_json(activity))
            elif activity.date_deadline == today:
                groups[1][1].append(_activity_to_json(activity))
            elif activity.date_deadline == today + datetime.timedelta(days=1):
                groups[2][1].append(_activity_to_json(activity))
            else:
                groups[3][1].append(_activity_to_json(activity))

        return [g for g in groups if g[1]]

    @http.route('/mail_plugin/activity/done', type='jsonrpc', auth='outlook', cors='*')
    def mail_activity_done(self, activity_id):
        request.env["mail.activity"].browse(int(activity_id)).action_done()
        return {'ok': True}

    @http.route('/mail_plugin/activity/cancel', type='jsonrpc', auth='outlook', cors='*')
    def mail_activity_cancel(self, activity_id):
        request.env["mail.activity"].browse(int(activity_id)).action_cancel()
        return {'ok': True}

    @http.route('/mail_plugin/activity/edit', type='jsonrpc', auth='outlook', cors='*')
    def mail_activity_edit(self, activity_id, summary, date_deadline_timestamp):
        activity = request.env["mail.activity"].browse(int(activity_id))
        activity.write({
            'summary': summary,
            'date_deadline': datetime.datetime.fromtimestamp(
                date_deadline_timestamp).date(),
        })
        return self.mail_activity_get()

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
        if model != "res.partner" or model not in self._mail_models_access_whitelist('read'):
            raise Forbidden()

        if isinstance(query, str):
            queries = [query]
        else:
            queries = query

        domain = Domain.FALSE
        for term in queries:
            normalized_email = tools.email_normalize(term)
            if normalized_email:
                filter_domain = [('email_normalized', 'ilike', term)]
            else:
                filter_domain = ['|', '|', ('complete_name', 'ilike', term), ('ref', '=', term),
                                 ('email', 'ilike', term)]
            domain |= Domain(filter_domain)

        # Search for the partner based on the email.
        # If multiple are found, take the first one.
        partners = request.env['res.partner'].search(domain, limit=limit)
        record_count = request.env['res.partner'].search_count(domain)
        return [
            self._get_partner_values(partner)
            for partner in partners
        ], record_count

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
        if p := request.env["res.partner"].search([('email', '=', email), ('name', '=', name)], limit=1):
            return p

        notification_emails = request.env['mail.alias.domain'].sudo().search([]).mapped('default_from_email')
        if tools.email_normalize(email) in notification_emails:
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
        allowed_model = self._mail_models_access_whitelist('write')
        if model not in allowed_model:
            _logger.error("Mail Plugin: can not log email on %s#%i (%s allowed)", model, res_id, allowed_model)
            raise Forbidden()

        if attachments:
            attachments = [
                (name, base64.b64decode(content))
                for name, content in attachments
            ]

        request.env[model].browse(res_id).message_post(
            body=Markup(message),
            attachments=attachments,
            message_type='comment',
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
        partner_values['company_name'] = partner.parent_id.name

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
