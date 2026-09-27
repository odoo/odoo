# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger, urls

from odoo.addons.base.tests.common import BaseCommon


@tagged('-at_install', 'post_install')
class TestPortalAdditionalIdentifiers(BaseCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_fr = cls.quick_ref('base.fr')
        cls.country_be = cls.quick_ref('base.be')
        cls.portal_user = cls._create_new_portal_user()
        cls.partner = cls.portal_user.partner_id
        cls.partner.country_id = cls.country_fr
        cls.default_address_values = {
            'name': 'Customer',
            'email': 'customer@example.com',
            'street': '12 rue de Rivoli',
            'city': 'Paris',
            'zip': '75001',
            'country_id': cls.country_fr.id,
            'phone': '+33123456789',
        }
        cls.submit_url = urls.urljoin(cls.base_url(), '/my/address/submit')

    def _submit(self, values):
        payload = {k: (str(v) if isinstance(v, float) else v) for k, v in values.items()}
        return self.url_open(self.submit_url, data=payload).json()

    def _base_values(self, **extra):
        return {
            **self.default_address_values,
            'csrf_token': self.csrf_token(),
            'partner_id': self.partner.id,
            **extra,
        }

    def test_country_info_route_returns_address_country_identifiers(self):
        """The country_info route exposes the country's identifiers so the form can refresh
        them when the customer changes the country (no FR identifier for a BE address)."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        fr_info = self.make_jsonrpc_request(
            f'/my/address/country_info/{self.country_fr.id}', {'address_type': 'billing'},
        )
        self.assertIn('FR_CN', fr_info['additional_identifiers_metadata'])
        be_info = self.make_jsonrpc_request(
            f'/my/address/country_info/{self.country_be.id}', {'address_type': 'billing'},
        )
        self.assertNotIn('FR_CN', be_info['additional_identifiers_metadata'])

    def test_add_and_remove_additional_identifier_tour(self):
        """The customer can add an identifier from the dropdown and remove it again."""
        self.start_tour(
            '/my/address?address_type=billing',
            'account.portal_additional_identifiers',
            login=self.portal_user.login,
        )

    def test_additional_identifier_saved(self):
        """A submitted additional identifier is stored in 'additional_identifiers'."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        res = self._submit(self._base_values(FR_CN='295109912611193'))
        self.assertEqual(res, {'redirectUrl': '/my/addresses'})
        self.assertEqual(self.partner.additional_identifiers, {'FR_CN': '295109912611193'})

    def test_additional_identifier_removed(self):
        """Submitting an empty value clears a previously saved identifier."""
        self.partner.sudo().additional_identifiers = {'FR_CN': '295109912611193'}
        self.authenticate(self.portal_user.login, self.portal_user.login)
        res = self._submit(self._base_values(FR_CN=''))
        self.assertEqual(res, {'redirectUrl': '/my/addresses'})
        self.assertFalse(self.partner.additional_identifiers)

    @mute_logger('odoo.http')
    def test_invalid_additional_identifier_rejected(self):
        """An invalid identifier value highlights its own input and is not saved."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        res = self._submit(self._base_values(FR_CN='not-a-nir'))
        self.assertIn('FR_CN', res['invalid_fields'])
        self.assertFalse(self.partner.additional_identifiers)

    @mute_logger('odoo.http')
    def test_individual_identifier_conflicts_with_vat(self):
        """A citizen number cannot be combined with a VAT number."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        res = self._submit(self._base_values(
            vat='FR23334175221',  # valid FR VAT (a company identifier)
            FR_CN='295109912611193',  # an individual identifier
        ))
        self.assertIn('FR_CN', res['invalid_fields'])
