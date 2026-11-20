# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.fields import Domain
from odoo.http import request
from odoo.addons.mass_mailing.controllers import main
from odoo.addons.website_mass_mailing.controllers.main import MassMailController as WebsiteMassMailingController


class MassMailController(main.MassMailController):

    def _get_value(self, subscription_type):
        value = super(MassMailController, self)._get_value(subscription_type)
        if not value and subscription_type == 'mobile':
            if not request.env.user._is_public():
                value = request.env.user.partner_id.phone
            elif request.session.get('mass_mailing_mobile'):
                value = request.session['mass_mailing_mobile']
        return value

    def _get_fname(self, subscription_type):
        value_field = super(MassMailController, self)._get_fname(subscription_type)
        if not value_field and subscription_type == 'mobile':
            value_field = 'mobile'
        return value_field

    @staticmethod
    def subscribe_to_newsletter(subscription_type, value, list_id, fname, address_name=None):
        if subscription_type != 'mobile':
            return WebsiteMassMailingController.subscribe_to_newsletter(subscription_type, value, list_id, fname, address_name)

        country = request.env.user.partner_id.country_id
        if not country and request.geoip.country_code:
            country = request.env['res.country'].sudo().search([
                ('code', '=', request.geoip.country_code),
            ], limit=1)
        country = country or request.env.company.country_id

        phone_sanitized = request.env['mailing.contact']._phone_format(number=value, country=country)
        if not value or not phone_sanitized:
            return {
                'toast_type': 'danger',
                'toast_content': _("Invalid phone number."),
            }

        MailingListSudo = request.env['mailing.list'].sudo()
        mailing_list = MailingListSudo.browse(int(list_id)).exists()

        if mailing_list and not request.env.user._is_internal() and not mailing_list.is_public:
            return {
                'toast_type': 'danger',
                'toast_content': _("Invalid mailing list."),
            }

        request.session[f'mass_mailing_{fname}'] = value

        ContactSudo = request.env['mailing.contact'].sudo().with_context(active_test=False)
        contacts = ContactSudo.search(
            Domain('mobile', '=', value)
          | Domain('phone_sanitized', '=', phone_sanitized))

        partner = request.env.user.partner_id
        is_own_phone = not request.env.user._is_public() and ((partner.phone == value) or (partner.phone_sanitized == phone_sanitized))
        if not contacts:
            if is_own_phone:
                contacts = ContactSudo.create(ContactSudo._from_partners_get_create_vals(partner))
            else:
                contacts = ContactSudo.create({
                    'name': value,
                    'mobile': value,
                })
        elif is_own_phone:
            contacts.filtered(lambda contact: not contact.partner_id).partner_id = partner

        if mailing_list and contacts:
            mailing_list._update_subscription_from_contacts(contacts, opt_out=False)
