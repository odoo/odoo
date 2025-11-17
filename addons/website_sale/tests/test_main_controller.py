# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment.models.payment_provider import PaymentProvider
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestPaymentProviderVisibility(PaymentHttpCommon, SaleCommon):

    def test_payment_provider_visibility_with_portal(self):
        """Check providers availability on the sales portal.

        The current website must be considered to filter the providers.
        """
        website_portal = self.env['website'].get_current_website()
        website_shop = self.env['website'].create({'name': "Shop Website"})

        base_url = self.env['ir.config_parameter'].sudo().get_base_url()
        website_portal.write({'domain': base_url})

        self.provider.write({'website_id': website_portal.id})
        restricted_provider = self.env['payment.provider'].sudo().search([('name', '=', 'Demo')])
        restricted_provider.write({'state': 'test', 'website_id': website_shop.id})

        url_so = self.sale_order.get_portal_url()
        self.sale_order.require_payment = True
        portal_url = f"{website_portal.domain}{url_so}"

        with patch(
            'odoo.addons.website_payment.models.payment_provider.PaymentProvider._get_compatible_providers',
            side_effect=lambda *args, **kwargs: PaymentProvider._get_compatible_providers(
                self.env['payment.provider'], *args, **kwargs
            ),
        ) as mock_method:
            self.url_open(portal_url, allow_redirects=True)

            mock_method.assert_called_once()
            self.assertEqual(mock_method.call_args.kwargs['website_id'], website_portal.id)

        mock_method.call_args.kwargs.pop('show_non_tokenize_provider', None)
        providers = self.env['payment.provider']._get_compatible_providers(
            *mock_method.call_args.args, **mock_method.call_args.kwargs
        )

        self.assertIn(self.provider.id, providers.ids, "The visible provider should be visible.")

        self.assertNotIn(
            restricted_provider.id, providers.ids, "The restricted provider shouldn't be visible."
        )
