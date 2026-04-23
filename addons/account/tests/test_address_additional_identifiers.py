# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.tools import urls

from odoo.addons.base.tests.common import BaseCommon


@tagged('-at_install', 'post_install')
class TestAddressAdditionalIdentifiers(BaseCommon, HttpCase):
    """The checkout/portal address form offers the additional identifiers
    (citizen numbers, passport, ...) of the address (partner) country, and keeps
    them in sync when the customer changes the country.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_ar = cls.quick_ref('base.ar')
        cls.country_be = cls.quick_ref('base.be')
        cls.env.company.write({
            'country_id': cls.country_ar.id,
            'account_fiscal_country_id': cls.country_ar.id,
        })
        cls.portal_user = cls._create_new_portal_user()
        # The offered identifiers are based on the address (partner) country, not the company.
        cls.portal_user.partner_id.country_id = cls.country_ar
        cls.address_url = urls.urljoin(cls.base_url(), '/my/address')

    def test_address_form_offers_address_country_identifiers(self):
        """The billing address form keeps the VAT field and offers the address country's
        identifiers (passport included)."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        partner = self.portal_user.partner_id
        res = self.url_open(f'{self.address_url}?partner_id={partner.id}&address_type=billing')
        html = res.text
        # The VAT field is kept and the identifiers block is rendered for the AR address.
        self.assertIn('name="vat"', html)
        self.assertIn('o_additional_identifiers_portal', html)
        # Argentinean identifiers (and the passport) are offered in the "Add identifier" list.
        self.assertIn('name="additional_identifier_AR_DNI"', html)
        self.assertIn('name="additional_identifier_PASSPORT"', html)
        # Each identifier can be removed through a dedicated button.
        self.assertIn('o_remove_identifier', html)

    def test_country_info_route_returns_address_country_identifiers(self):
        """The country_info route exposes the country's identifiers so the form can refresh
        them when the customer changes the country (no AR identifier for a BE address)."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        ar_info = self.make_jsonrpc_request(
            f'/my/address/country_info/{self.country_ar.id}', {'address_type': 'billing'},
        )
        self.assertIn('AR_DNI', ar_info['additional_identifiers_metadata'])
        be_info = self.make_jsonrpc_request(
            f'/my/address/country_info/{self.country_be.id}', {'address_type': 'billing'},
        )
        self.assertNotIn('AR_DNI', be_info['additional_identifiers_metadata'])

    def test_add_and_remove_additional_identifier_tour(self):
        """The customer can add an identifier from the dropdown and remove it again."""
        self.start_tour(
            '/my/address?address_type=billing',
            'account.additional_identifiers',
            login=self.portal_user.login,
        )
