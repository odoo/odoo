from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.integration.tools import get_api_client
from odoo.addons.integration.tools.api_client import is_private_host

_RESOLVER = "socket.getaddrinfo"


def _addrinfo(*ips):
    return [(None, None, None, None, (ip, 0)) for ip in ips]


@tagged("post_install", "-at_install")
class TestIsPrivateHost(TransactionCase):
    def test_literal_private_addresses(self):
        for host in (
            "127.0.0.1",
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
            "169.254.1.1",
            "::1",
            "[fe80::1]",
            "fc00::1",
        ):
            with self.subTest(host=host):
                self.assertTrue(is_private_host(host))

    def test_literal_public_addresses(self):
        for host in ("8.8.8.8", "2001:4860:4860::8888"):
            with self.subTest(host=host):
                self.assertFalse(is_private_host(host))

    def test_a_literal_address_is_not_looked_up(self):
        with patch(_RESOLVER) as resolver:
            is_private_host("10.0.0.1")
        resolver.assert_not_called()

    def test_carrier_grade_nat_is_not_private(self):
        self.assertFalse(is_private_host("100.64.0.1"))

    def test_a_suffix_name_resolving_publicly_is_public(self):
        with patch(_RESOLVER, return_value=_addrinfo("93.184.216.34")):
            self.assertFalse(is_private_host("foo.internal"))

    def test_a_public_name_resolving_privately_is_private(self):
        with patch(_RESOLVER, return_value=_addrinfo("127.0.0.1")):
            self.assertTrue(is_private_host("localtest.me"))

    def test_a_name_with_one_public_address_is_public(self):
        with patch(_RESOLVER, return_value=_addrinfo("10.0.0.1", "8.8.8.8")):
            self.assertFalse(is_private_host("split.example"))

    def test_a_name_with_only_private_addresses_is_private(self):
        with patch(_RESOLVER, return_value=_addrinfo("10.0.0.1", "192.168.1.1")):
            self.assertTrue(is_private_host("internal.example"))

    def test_an_unresolvable_suffix_name_keeps_the_fallback(self):
        with patch(_RESOLVER, side_effect=OSError("no such host")):
            self.assertTrue(is_private_host("printer.local"))
            self.assertTrue(is_private_host("localhost"))

    def test_an_unresolvable_ordinary_name_is_not_private(self):
        with patch(_RESOLVER, side_effect=OSError("no such host")):
            self.assertFalse(is_private_host("api.example.com"))

    def test_an_empty_host_is_not_private(self):
        self.assertFalse(is_private_host(""))
        self.assertFalse(is_private_host(None))


@tagged("post_install", "-at_install")
class TestTlsGuardsUseIt(TransactionCase):
    _sequence = 0

    def _endpoint(self, url, verify_tls=True):
        type(self)._sequence += 1
        return self.env["integration.service"].create(
            {
                "name": "tls probe",
                "code": f"tls_probe_{self._sequence}",
                "endpoint_url": url,
                "auth_type": "none",
                "verify_tls": verify_tls,
            }
        )

    def test_the_constraint_refuses_a_suffix_name_that_resolves_publicly(self):
        with patch(_RESOLVER, return_value=_addrinfo("93.184.216.34")):
            with self.assertRaises(ValidationError) as caught:
                self._endpoint("https://foo.internal/api", verify_tls=False)
        self.assertIn("private network", str(caught.exception))

    def test_the_constraint_allows_a_genuinely_private_host(self):
        with patch(_RESOLVER, return_value=_addrinfo("10.0.0.5")):
            endpoint = self._endpoint("https://device.example/api", verify_tls=False)
        self.assertFalse(endpoint.verify_tls)

    def test_verification_on_needs_no_lookup(self):
        endpoint = self._endpoint("https://api.example.com/v1")
        self.assertTrue(endpoint.verify_tls)

        client = get_api_client(self.env, endpoint.code)
        with patch(_RESOLVER) as resolver:
            self.assertTrue(client._get_tls_verification(endpoint.endpoint_url))
        resolver.assert_not_called()
