# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.payment.models.payment_provider import PaymentProvider
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale.tests.common import SaleCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale


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
        restricted_provider = self.env['payment.provider'].sudo().search([('name', '=', 'Demo'), ('company_id', '=', website_shop.company_id.id)])
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


@tagged('post_install', '-at_install')
class TestAttributeValueParsing(TransactionCase):

    def test_valid_attribute_values(self):
        """Well-formed query params keep grouping value ids by attribute id."""
        self.assertEqual(
            WebsiteSale._get_attribute_value_dict(['1-2,3']),
            {1: [2, 3]},
        )
        self.assertEqual(
            WebsiteSale._get_attribute_value_dict(['1-2', '3-4,5']),
            {1: [2], 3: [4, 5]},
        )

    def test_malformed_attribute_values_are_ignored(self):
        """Non-digit parts come straight from a public URL and must not crash the shop.

        Each of these used to raise an uncaught ValueError (or IndexError) and render
        the bare "Internal Server Error" page instead of the product list.
        """
        for value in ('abc', ',,', '1,2', '1', '1--2', '1-', ' '):
            with self.subTest(value=value):
                self.assertEqual(
                    WebsiteSale._get_attribute_value_dict([value]),
                    {},
                    f"Malformed attribute_values {value!r} should be ignored.",
                )

    def test_malformed_value_ids_dont_discard_valid_ones(self):
        """A bad value id must not take down the valid ids of the same attribute."""
        self.assertEqual(
            WebsiteSale._get_attribute_value_dict(['1-2,']),
            {1: [2]},
        )
        self.assertEqual(
            WebsiteSale._get_attribute_value_dict(['1-,,2']),
            {1: [2]},
        )

    def test_malformed_parts_dont_discard_valid_ones(self):
        """A malformed part must not take down the valid parts of the same request."""
        self.assertEqual(
            WebsiteSale._get_attribute_value_dict(['1-2,abc,3', 'nope', '5-6']),
            {1: [2, 3], 5: [6]},
        )
