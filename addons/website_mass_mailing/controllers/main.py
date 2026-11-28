# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.exceptions

from odoo import tools, _
from odoo.exceptions import UserError
from odoo.http import route, request
from odoo.addons.mass_mailing.controllers import main


class MassMailController(main.MassMailController):

    @route('/website_mass_mailing/is_subscriber', type='jsonrpc', website=True, auth='public')
    def is_subscriber(self, list_id, subscription_type, **post):
        """Tell whether the visitor is already subscribed to a mailing list.

        :param int list_id: the `mailing.list` to check.
        :param str subscription_type: contact field the subscription is based on, e.g. 'email'.
        :return: dict with `is_subscriber`, the `value` identifying the visitor (their email
            address for instance) and `warn_missing_list`, set when the list is gone.
        :rtype: dict
        """
        mailing_list_su = request.env['mailing.list'].browse(int(list_id)).sudo()
        if request.env.user._is_internal() and not mailing_list_su.exists().active:
            return {'is_subscriber': False, 'value': '', 'warn_missing_list': True}
        value = self._get_value(subscription_type)
        fname = self._get_fname(subscription_type)
        is_subscriber = False
        if value and fname:
            contacts_count = request.env['mailing.subscription'].sudo().search_count(
                [('list_id', 'in', [int(list_id)]), (f'contact_id.{fname}', '=', value), ('opt_out', '=', False)])
            is_subscriber = contacts_count > 0

        return {'is_subscriber': is_subscriber, 'value': value, 'warn_missing_list': False}

    def _get_value(self, subscription_type):
        value = None
        if subscription_type == 'email':
            if not request.env.user._is_public():
                value = request.env.user.email
            elif request.session.get('mass_mailing_email'):
                value = request.session['mass_mailing_email']
        return value

    def _get_fname(self, subscription_type):
        return 'email' if subscription_type == 'email' else ''

    @route('/website_mass_mailing/subscribe', type='jsonrpc', website=True, auth='public')
    def subscribe(self, list_id, value, subscription_type, **post):
        """Subscribe an email or phone number to a mailing list (newsletter signup).

        :param int list_id: id of the `mailing.list` to subscribe to.
        :param str value: the email address or phone number to subscribe.
        :param str subscription_type: 'email' or 'mobile', matching the type of `value`.
        :return: {'toast_type': 'success'|'danger', 'toast_content': message to show}
        :rtype: dict
        """
        try:
            request.env['ir.http']._verify_request_recaptcha_token('website_mass_mailing_subscribe')
        except UserError as e:
            return {
                'toast_type': 'danger',
                'toast_content': str(e),
            }

        fname = self._get_fname(subscription_type)
        # TODO in master: we no longer display the toast on success, so update
        # the return.
        return self.subscribe_to_newsletter(subscription_type, value, list_id, fname) or {
            'toast_type': 'success',
            'toast_content': _("Thanks for subscribing!"),
        }

    @staticmethod
    def subscribe_to_newsletter(subscription_type, value, list_id, fname, address_name=None):
        if subscription_type != 'email':
            raise werkzeug.exceptions.BadRequest(_('Invalid subscription type'))

        name, email_normalized = tools.parse_contact_from_email(value)
        if not value or not email_normalized:
            return {
                'toast_type': 'danger',
                'toast_content': _("Invalid email."),
            }

        MailingListSudo = request.env['mailing.list'].sudo()
        mailing_list = MailingListSudo.browse(int(list_id)).exists()

        if mailing_list and not request.env.user._is_internal() and not mailing_list.is_public:
            return {
                'toast_type': 'danger',
                'toast_content': _("Invalid mailing list."),
            }

        request.session[f'mass_mailing_{fname}'] = email_normalized

        ContactSudo = request.env['mailing.contact'].sudo().with_context(active_test=False)
        contacts = ContactSudo.search([
            ('email_normalized', '=', email_normalized),
        ])

        partner = request.env.user.partner_id
        is_own_email = not request.env.user._is_public() and partner.email_normalized == email_normalized
        if not contacts:
            if is_own_email:
                contacts = ContactSudo.create(ContactSudo._from_partners_get_create_vals(partner))
            else:
                contacts = ContactSudo.create({
                    'name': name or address_name,
                    'email': email_normalized,
                })
        elif is_own_email:
            contacts.filtered(lambda contact: not contact.partner_id).partner_id = partner

        if mailing_list and contacts:
            mailing_list._update_subscription_from_contacts(contacts, opt_out=False)
