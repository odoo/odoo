# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools, _
from odoo.http import route, request
from odoo.addons.mass_mailing.controllers import main


class MassMailController(main.MassMailController):

    @route('/website_mass_mailing/is_subscriber', type='json', website=True, auth='public')
    def is_subscriber(self, list_id, subscription_type, **post):
        value = self._get_value(subscription_type)
        fname = self._get_fname(subscription_type)
        is_subscriber = False
        if value and fname:
            contacts_count = request.env['mailing.subscription'].sudo().search_count(
                [('list_id', 'in', [int(list_id)]), (f'contact_id.{fname}', '=', value), ('opt_out', '=', False)])
            is_subscriber = contacts_count > 0

        return {'is_subscriber': is_subscriber, 'value': value}

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

    @route('/website_mass_mailing/subscribe', type='json', website=True, auth='public')
    def subscribe(self, list_id, value, subscription_type, **post):
        if not request.env['ir.http']._verify_request_recaptcha_token('website_mass_mailing_subscribe'):
            return {
                'toast_type': 'danger',
                'toast_content': _("Suspicious activity detected by Google reCaptcha."),
            }

        fname = self._get_fname(subscription_type)
        self.subscribe_to_newsletter(subscription_type, value, list_id, fname)
        return {
            'toast_type': 'success',
            'toast_content': _("Thanks for subscribing!"),
        }

    @staticmethod
    def subscribe_to_newsletter(subscription_type, value, list_id, fname, address_name=None):
        ContactSubscription = request.env['mailing.subscription'].sudo()
        Contacts = request.env['mailing.contact'].sudo()
        if subscription_type == 'email':
            name, value = tools.parse_contact_from_email(value)
            if not name:
                name = address_name
        elif subscription_type == 'mobile':
            name = value

        subscription = ContactSubscription.search(
            [('list_id', '=', int(list_id)), (f'contact_id.{fname}', '=', value)], limit=1)
        if not subscription:
            # inline add_to_list as we've already called half of it
            contact_id = Contacts.search([(fname, '=', value)], limit=1)
            if not contact_id:
                contact_id = Contacts.create({'name': name, fname: value})
            ContactSubscription.create({'contact_id': contact_id.id, 'list_id': int(list_id)})
        elif subscription.opt_out:
            subscription.opt_out = False
        # add email to session
        request.session[f'mass_mailing_{fname}'] = value
