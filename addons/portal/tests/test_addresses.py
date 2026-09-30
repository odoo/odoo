# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Request
from odoo.tests import HttpCase, tagged
from odoo.tests.common import JsonRpcException
from odoo.tools import mute_logger, urls

from odoo.addons.base.tests.common import BaseCommon


@tagged('-at_install', 'post_install')
class TestPortalAddresses(BaseCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_be = cls.quick_ref('base.be')
        cls.env.company.country_id = cls.country_be
        cls.portal_user = cls._create_new_portal_user()
        cls.internal_user = cls._create_new_internal_user()
        cls.default_address_values = {
            'name': 'Odoo Farm 3',
            'email': 'o@d.oo',
            'street': 'Rue de Ramillies 1',
            'city': 'Ramillies',
            'zip': '1367',
            'country_id': cls.country_be.id,
            'phone': '+323333333333333',
        }
        base_url = cls.base_url()
        cls.submit_url = urls.urljoin(base_url, '/my/address/submit')
        cls.archive_url = urls.urljoin(base_url, '/my/address/archive')

        # Company tree-like hierarchy
        #       Company
        #       /     \
        #      A       B
        cls.account_a = cls._create_new_portal_user(login='portal_a')
        cls.account_b = cls._create_new_portal_user(login='portal_b')
        cls.company_partner = cls.env['res.partner'].create({
            'name': 'Test Odoo SA',
            'is_company': True,
            'email': 'odoo@odoo.com',
            'street': 'Chau. de Namur 40',
            'city': 'Ramillies',
            'zip': '1367',
            'country_id': cls.country_be.id,
            'phone': '+3200000000000',
        })
        (cls.account_a.partner_id + cls.account_b.partner_id).write({
            'parent_id': cls.company_partner.id,
        })

    # Some utils c/p from payment http_common
    def _make_http_post_request(self, url, data=None):
        """ Make an HTTP POST request to the provided URL.

        :param str url: The URL to make the request to
        :param dict data: The data to be send in the request body
        :return: The response of the request
        :rtype: :class:`requests.models.Response`
        """
        formatted_data = self._format_http_request_payload(payload=data)
        return self.url_open(url, data=formatted_data)

    def _format_http_request_payload(self, payload=None):
        """ Format a request payload to replace float values by their string representation.

        :param dict payload: The payload to format
        :return: The formatted payload
        :rtype: dict
        """
        formatted_payload = {}
        if payload is not None:
            for k, v in payload.items():
                formatted_payload[k] = str(v) if isinstance(v, float) else v
        return formatted_payload

    def _submit_address_values(self, values):
        return self._make_http_post_request(self.submit_url, values).json()

    def test_required_values(self):
        """Check that empty values for required fields are correctly caught."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)
        for fname in ('name', 'email', 'street', 'city', 'country_id', 'phone'):
            res = self._submit_address_values({
                **self.default_address_values,
                'csrf_token': csrf_token,
                'partner_id': self.portal_user.partner_id.id,
                fname: '',
            })
            self.assertIn(fname, res['invalid_fields'])

    def test_email_validation(self):
        """Check that wrong email values are correctly caught."""
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)
        res = self._submit_address_values({
            **self.default_address_values,
            'csrf_token': csrf_token,
            'email': 'hello',
            'street': False,
        })
        self.assertIn('email', res['invalid_fields'])
        res = self._submit_address_values({
            **self.default_address_values,
            'csrf_token': csrf_token,
            'email': 'hello@.com',
            'street': False,
        })
        self.assertIn('email', res['invalid_fields'])
        res = self._submit_address_values({
            **self.default_address_values,
            'csrf_token': csrf_token,
            'email': 'hello@oo.',
            'street': False,
        })
        self.assertIn('email', res['invalid_fields'])

    def test_internal_user_cannot_update_name(self):
        self.authenticate(self.internal_user.login, self.internal_user.login)
        csrf_token = Request.csrf_token(self)

        internal_partner = self.internal_user.partner_id
        # Fill the incomplete address
        internal_partner.write(self.default_address_values)

        # Try to update the account name
        res = self._submit_address_values({
            **self.default_address_values,
            'name': 'My name is nobody',
            'csrf_token': csrf_token,
            'partner_id': internal_partner.id,
        })
        self.assertIn('name', res['invalid_fields'])

    def test_internal_user_cannot_update_email(self):
        self.authenticate(self.internal_user.login, self.internal_user.login)
        csrf_token = Request.csrf_token(self)

        internal_partner = self.internal_user.partner_id
        # Fill the incomplete address
        internal_partner.write(self.default_address_values)

        # Try to update the account email
        res = self._submit_address_values({
            **self.default_address_values,
            'email': 'new_email@hohoho.com',
            'csrf_token': csrf_token,
            'partner_id': internal_partner.id,
        })
        self.assertIn('email', res['invalid_fields'])

    def test_vat_update(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)

        res = self._submit_address_values({
            **self.default_address_values,
            'vat': 'BE0926372368',
            'csrf_token': csrf_token,
            'partner_id': self.portal_user.partner_id.id,
        })
        self.assertEqual(res, {'redirectUrl': '/my/addresses'})
        self.assertRecordValues(
            self.portal_user.partner_id,
            [{**self.default_address_values, 'vat': 'BE0926372368'}],
        )

    def test_cannot_update_vat_on_child_addresses(self):
        """Check that the VAT cannot be updated on a child address.

        Customers are supposed to update it through their main address (and the route /my/account)
        """
        self.authenticate(self.account_a.login, self.account_a.login)
        csrf_token = Request.csrf_token(self)

        res = self._submit_address_values({
            **self.default_address_values,
            'vat': 'BE0926372368',
            'csrf_token': csrf_token,
            'partner_id': self.account_a.partner_id.id,
        })
        self.assertIn('vat', res['invalid_fields'])

    def test_main_address_update(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)

        res = self._submit_address_values({
            **self.default_address_values,
            'csrf_token': csrf_token,
            'partner_id': self.portal_user.partner_id.id,
        })
        self.assertEqual(res, {'redirectUrl': '/my/addresses'})
        self.assertRecordValues(
            self.portal_user.partner_id,
            [self.default_address_values],
        )

    def test_success_url(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)

        res = self._submit_address_values({
            **self.default_address_values,
            'csrf_token': csrf_token,
            'partner_id': self.portal_user.partner_id.id,
            'callback': '/my/beautiful/url',
        })
        self.assertEqual(res, {'redirectUrl': '/my/beautiful/url'})
        self.assertRecordValues(
            self.portal_user.partner_id,
            [self.default_address_values],
        )

    def test_billing_address_creation(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)

        res = self._submit_address_values({
            **self.default_address_values,
            'csrf_token': csrf_token,
            'address_type': 'billing',
        })
        self.assertEqual(res, {'redirectUrl': '/my/addresses'})
        billing_address = self.portal_user.partner_id.child_ids
        self.assertTrue(len(billing_address) == 1)
        self.assertEqual(billing_address.type, 'invoice')
        self.assertRecordValues(
            self.portal_user.partner_id.child_ids,
            [self.default_address_values],
        )

    def test_delivery_address_creation(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)

        res = self._submit_address_values({
            **self.default_address_values,
            'csrf_token': csrf_token,
            'address_type': 'delivery',
        })
        self.assertEqual(res, {'redirectUrl': '/my/addresses'})
        delivery_address = self.portal_user.partner_id.child_ids
        self.assertTrue(len(delivery_address) == 1)
        self.assertEqual(delivery_address.type, 'delivery')
        self.assertRecordValues(
            self.portal_user.partner_id.child_ids,
            [self.default_address_values],
        )

    def test_delivery_use_as_billing_address_creation(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        csrf_token = Request.csrf_token(self)

        res = self._submit_address_values({
            **self.default_address_values,
            'csrf_token': csrf_token,
            'address_type': 'delivery',
            'use_delivery_as_billing': '1',
        })
        self.assertEqual(res, {'redirectUrl': '/my/addresses'})
        delivery_address = self.portal_user.partner_id.child_ids
        self.assertTrue(len(delivery_address) == 1)
        self.assertEqual(delivery_address.type, 'other')
        self.assertRecordValues(
            self.portal_user.partner_id.child_ids,
            [self.default_address_values],
        )

    # def test_billing_address_update(self):

    # def test_delivery_address_update(self):

    def test_address_archiving(self):
        self.authenticate(self.account_a.login, self.account_a.login)

        # Address doesn't belong to logged in user
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                self.archive_url, params={'partner_id': self.portal_user.partner_id.id},
            )

        # Cannot archive main address of customer
        with self.assertRaises(JsonRpcException), mute_logger('odoo.http'):
            self.make_jsonrpc_request(
                self.archive_url, params={'partner_id': self.account_a.partner_id.id},
            )

        # Cannot archive a contact address, even if it belongs to the user commercial partner
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                self.archive_url, params={'partner_id': self.account_b.partner_id.id},
            )

        child_partner = self.env['res.partner'].create({
            'parent_id': self.account_a.partner_id.id,
            'type': 'delivery',
            'street': 'Nowhere',
            'name': 'Nobody',
        })
        self.assertTrue(child_partner.active)
        self.make_jsonrpc_request(
            self.archive_url, params={'partner_id': child_partner.id},
        )
        self.assertFalse(child_partner.active)
