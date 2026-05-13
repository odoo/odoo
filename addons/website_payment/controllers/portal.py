# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
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
        limit = self._cast_as_int(limit)

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
        # Select the brands, i.e. non-primary payment methods. E.g., Amex for Card.
        brands_domain = Domain([
            ('is_primary', '=', False),
            ('primary_payment_method_id.provider_id', 'in', available_providers_sudo.ids),
            ('primary_payment_method_id.active', '=', True),
        ])
        # Or, select the primary payment methods without any brands. E.g., PayPal.
        primary_without_brands_domain = Domain([
            ('is_primary', '=', True),
            ('brand_ids', '=', False),
            ('provider_id', 'in', available_providers_sudo.ids),
        ])

        supported_pms = request.env['payment.method'].search(
            Domain.OR([brands_domain, primary_without_brands_domain]),
            limit=limit,
        )._deduplicate_by_code().mapped(lambda pm: {
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


class PortalAccount(account_payment_portal.PortalAccount):
    def _invoice_get_page_view_values(self, *args, **kwargs):
        """Override of `account_payment` to make the providers filtering website-aware."""
        return super()._invoice_get_page_view_values(*args, website_id=self.env.website.id, **kwargs)
