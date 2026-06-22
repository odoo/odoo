# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.account_payment.controllers import portal as account_payment_portal
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    @route(
        '/website_payment/snippet/supported_payment_methods',
        type='http', methods=['GET'], auth='public', website=True, sitemap=False, readonly=True,
    )
    def get_supported_payment_methods(self, limit=None):
        """Retrieve the payment methods linked to payment providers published on the current
        website.

        If a payment method is a primary payment method, its brands are returned instead.

        Note: The provider must be linked to the same company as the website. This differs from the
        usual payment method selection, which uses the user's company. In this case, we want to
        display the general payment methods linked to the website, regardless of the user.

        :param int limit: The number of payment methods to return.
        :return: The supported payment methods, in [{'name': str, 'image_url': str}] format.
        :rtype: list[dict]
        """
<<<<<<< 92d5070c9ead8d4544e0380018a3dd0012fa329c
        limit = self._cast_as_int(limit)
||||||| 3393c5e57159e1749a52b35a092848d6ee5af953
        kwargs['is_donation'] = True
        kwargs['currency_id'] = self._cast_as_int(kwargs.get('currency_id')) or request.env.company.currency_id.id
        kwargs['amount'] = self._cast_as_float(kwargs.get('amount')) or 25.0
        kwargs['donation_options'] = kwargs.get('donation_options', json_safe.dumps(dict(customAmount="freeAmount")))
=======
        kwargs['is_donation'] = True

        if request.httprequest.method == 'POST':
            kwargs['donation_descriptions'] = request.httprequest.form.getlist('donation_descriptions')
            request.session['donation_pay_values'] = {
                key: kwargs[key]
                for key in ('amount', 'currency_id', 'donation_options', 'donation_descriptions')
                if key in kwargs
            }
            return request.redirect(request.httprequest.path, code=303)

        for key, value in request.session.get('donation_pay_values', {}).items():
            kwargs.setdefault(key, value)

        kwargs['currency_id'] = self._cast_as_int(kwargs.get('currency_id')) or request.env.company.currency_id.id
        kwargs['amount'] = self._cast_as_float(kwargs.get('amount')) or 25.0
        kwargs['donation_options'] = kwargs.get('donation_options', json_safe.dumps(dict(customAmount="freeAmount")))
>>>>>>> fb7e9231bf426333e15d6474a698d8f36f94a2ed

        # For any primary payment method with at least one compatible provider.
        available_providers_sudo = (
            request.env['payment.provider']
                # Force the public user such that editors see what customers will see
                .with_user(self.env.website.user_id)
                .sudo()  # Needed to read providers' fields with public user
                ._find_available_providers(
                    self.env.website.company_id.id, None, 0, website_id=self.env.website.id
                )
        )
        # For each available provider's primary payment method, show its active brands if any
        # (e.g. Amex/Visa for Card), otherwise show the primary payment method itself (e.g. PayPal)
        primary_pms_sudo = available_providers_sudo.primary_payment_method_ids.filtered("active")
        all_pms_sudo = primary_pms_sudo.mapped(
            lambda pm: pm.brand_ids.filtered("active") if pm.brand_ids else pm
        )

        supported_pms = all_pms_sudo._deduplicate_by_code()[:limit].mapped(lambda pm: {
            'name': pm.name,
            # Loading the image via this url caches the image on the client browser
            'image_url': request.env['website'].image_url(pm, 'image'),
        })

        if request.env.user._is_internal():
            # Ensure the internal users can always see the most up to date list of PMs.
            cache_control = 'no-cache'
        else:
            # Cache the PMs for public/portal users for 7 days, with an additional day to re-use
            # the stale PMs while a background task updates the client cache.
            cache_control = 'public, max-age=604800, stale-while-revalidate=86400'

        return request.make_json_response(
            supported_pms, headers=[('Cache-Control', cache_control)],
        )
<<<<<<< 92d5070c9ead8d4544e0380018a3dd0012fa329c
||||||| 3393c5e57159e1749a52b35a092848d6ee5af953
        tx_sudo.is_donation = True
        if use_public_partner:
            tx_sudo.update({
                'partner_name': details['name'],
                'partner_email': details['email'],
                'partner_country_id': int(details['country_id']),
            })
        elif not tx_sudo.partner_country_id:
            tx_sudo.partner_country_id = int(kwargs['partner_details']['country_id'])
        # the user can change the donation amount on the payment page,
        # therefor we need to recompute the access_token
        access_token = payment_utils.generate_access_token(
            tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id
        )
        self._update_landing_route(tx_sudo, access_token)

        # Send a notification to warn that a donation has been made
        recipient_email = kwargs['donation_recipient_email']
        comment = kwargs['donation_comment']
        tx_sudo._send_donation_email(True, comment, recipient_email)

        return tx_sudo._get_processing_values()

    def _get_extra_payment_form_values(
        self, donation_options=None, donation_descriptions=None, is_donation=False, **kwargs
    ):
        rendering_context = super()._get_extra_payment_form_values(
            donation_options=donation_options,
            donation_descriptions=donation_descriptions,
            is_donation=is_donation,
            **kwargs,
        )
        if is_donation:
            user_sudo = request.env.user
            logged_in = not user_sudo._is_public()
            # If the user is logged in, take their partner rather than the partner set in the params.
            # This is something that we want, since security rules are based on the partner, and created
            # tokens should not be assigned to the public user. This should have no impact on the
            # transaction itself besides making reconciliation possibly more difficult (e.g. The
            # transaction and invoice partners are different).
            partner_sudo = user_sudo.partner_id
            partner_details = {}
            if logged_in:
                partner_details = {
                    'name': partner_sudo.name,
                    'email': partner_sudo.email,
                    'country_id': partner_sudo.country_id.id,
                }

            countries = request.env['res.country'].sudo().search([])
            descriptions = request.httprequest.form.getlist('donation_descriptions')

            donation_options = json_safe.loads(donation_options) if donation_options else {}
            donation_amounts = json_safe.loads(donation_options.get('donationAmounts', '[]'))

            rendering_context.update({
                'is_donation': True,
                'partner': partner_sudo,
                'submit_button_label': _("Donate"),
                'transaction_route': '/donation/transaction/%s' % donation_options.get('minimumAmount', 0),
                'partner_details': partner_details,
                'error': {},
                'countries': countries,
                'donation_options': donation_options,
                'donation_amounts': donation_amounts,
                'donation_descriptions': descriptions,
            })
        return rendering_context

    def _get_payment_page_template_xmlid(self, **kwargs):
        if kwargs.get('is_donation'):
            return 'website_payment.donation_pay'
        return super()._get_payment_page_template_xmlid(**kwargs)

    @staticmethod
    def _compute_show_tokenize_input_mapping(providers_sudo, **kwargs):
        """ Override of `payment` to hide the "Save my payment details" input in the payment form
        when its a donation and user is not logged in.

        :param payment.provider providers_sudo: The providers for which to determine whether the
                                                tokenization input should be shown or not.
        :param dict kwargs: The optional data passed to the helper methods.
        :return: The mapping of the computed value for each provider id.
        :rtype: dict
        """
        res = super(PaymentPortal, PaymentPortal)._compute_show_tokenize_input_mapping(
            providers_sudo, **kwargs
        )
        if kwargs.get('is_donation') and request.env.user._is_public():
            for provider_sudo in providers_sudo:
                res[provider_sudo.id] = False
        return res
=======
        tx_sudo.is_donation = True
        if use_public_partner:
            tx_sudo.update({
                'partner_name': details['name'],
                'partner_email': details['email'],
                'partner_country_id': int(details['country_id']),
            })
        elif not tx_sudo.partner_country_id:
            tx_sudo.partner_country_id = int(kwargs['partner_details']['country_id'])
        # the user can change the donation amount on the payment page,
        # therefor we need to recompute the access_token
        access_token = payment_utils.generate_access_token(
            tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id
        )
        self._update_landing_route(tx_sudo, access_token)

        # Send a notification to warn that a donation has been made
        recipient_email = kwargs['donation_recipient_email']
        comment = kwargs['donation_comment']
        tx_sudo._send_donation_email(True, comment, recipient_email)

        return tx_sudo._get_processing_values()

    def _get_extra_payment_form_values(
        self, donation_options=None, donation_descriptions=None, is_donation=False, **kwargs
    ):
        rendering_context = super()._get_extra_payment_form_values(
            donation_options=donation_options,
            donation_descriptions=donation_descriptions,
            is_donation=is_donation,
            **kwargs,
        )
        if is_donation:
            user_sudo = request.env.user
            logged_in = not user_sudo._is_public()
            # If the user is logged in, take their partner rather than the partner set in the params.
            # This is something that we want, since security rules are based on the partner, and created
            # tokens should not be assigned to the public user. This should have no impact on the
            # transaction itself besides making reconciliation possibly more difficult (e.g. The
            # transaction and invoice partners are different).
            partner_sudo = user_sudo.partner_id
            partner_details = {}
            if logged_in:
                partner_details = {
                    'name': partner_sudo.name,
                    'email': partner_sudo.email,
                    'country_id': partner_sudo.country_id.id,
                }

            countries = request.env['res.country'].sudo().search([])
            descriptions = donation_descriptions or []

            donation_options = json_safe.loads(donation_options) if donation_options else {}
            donation_amounts = json_safe.loads(donation_options.get('donationAmounts', '[]'))

            rendering_context.update({
                'is_donation': True,
                'partner': partner_sudo,
                'submit_button_label': _("Donate"),
                'transaction_route': '/donation/transaction/%s' % donation_options.get('minimumAmount', 0),
                'partner_details': partner_details,
                'error': {},
                'countries': countries,
                'donation_options': donation_options,
                'donation_amounts': donation_amounts,
                'donation_descriptions': descriptions,
            })
        return rendering_context

    def _get_payment_page_template_xmlid(self, **kwargs):
        if kwargs.get('is_donation'):
            return 'website_payment.donation_pay'
        return super()._get_payment_page_template_xmlid(**kwargs)

    @staticmethod
    def _compute_show_tokenize_input_mapping(providers_sudo, **kwargs):
        """ Override of `payment` to hide the "Save my payment details" input in the payment form
        when its a donation and user is not logged in.

        :param payment.provider providers_sudo: The providers for which to determine whether the
                                                tokenization input should be shown or not.
        :param dict kwargs: The optional data passed to the helper methods.
        :return: The mapping of the computed value for each provider id.
        :rtype: dict
        """
        res = super(PaymentPortal, PaymentPortal)._compute_show_tokenize_input_mapping(
            providers_sudo, **kwargs
        )
        if kwargs.get('is_donation') and request.env.user._is_public():
            for provider_sudo in providers_sudo:
                res[provider_sudo.id] = False
        return res
>>>>>>> fb7e9231bf426333e15d6474a698d8f36f94a2ed


class PortalAccount(account_payment_portal.PortalAccount):
    def _invoice_get_page_view_values(self, *args, **kwargs):
        """Override of `account_payment` to make the providers filtering website-aware."""
        return super()._invoice_get_page_view_values(*args, website_id=self.env.website.id, **kwargs)
