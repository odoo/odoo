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
        try:
            self.subscribe_to_newsletter(subscription_type, value, list_id, fname)
        except werkzeug.exceptions.BadRequest as e:
            return {
                'toast_type': 'danger',
                'toast_content': str(e),
            }

        return {
            'toast_type': 'success',
            'toast_content': _("Thanks for subscribing!"),
        }

    @staticmethod
    def subscribe_to_newsletter(subscription_type, input_value, list_id, fname, address_name=None):
        Contacts = request.env['mailing.contact'].sudo()
        MailingList = request.env['mailing.list'].sudo()

        if subscription_type == 'email':
            name, value = tools.parse_contact_from_email(input_value)
            if not name:
                name = address_name
            fname_normalized = 'email_normalized'
            contact_fname_normalized = fname_normalized
        elif subscription_type == 'mobile':
            name = address_name or input_value
            value = input_value
            fname_normalized = 'phone_sanitized'
            contact_fname_normalized = fname_normalized if fname_normalized in Contacts else 'mobile'
        else:
            raise werkzeug.exceptions.BadRequest(_('Invalid subscription type `%(type)s`', type=subscription_type))
        if not value:
            raise werkzeug.exceptions.BadRequest(_('Invalid subscription value `%(value)s`', value=input_value or ''))

        # fetch mialing list -> if it does not exist, just skip subscribe, but keep contact management
        mailing_list = MailingList.browse(int(list_id)).exists()

        # add field to session
        request.session[f'mass_mailing_{fname}'] = input_value

        # fetch contact information
        contact = Contacts.search(
            ['|', (fname, '=', value), (contact_fname_normalized, '=', value)],
            limit=1,
        )
        contact_partner = request.env.user.partner_id if (
            not request.env.user.is_public and
            request.env.user.partner_id[fname_normalized] == value
        ) else request.env['res.partner']
        if contact:
            if contact_partner and not contact.partner_id:
                contact.partner_id = contact_partner.id
        else:
            contact = Contacts.create({'name': name, fname: value, 'partner_id': contact_partner.id})

        return mailing_list._update_subscription_from_email(value, opt_out=False)
