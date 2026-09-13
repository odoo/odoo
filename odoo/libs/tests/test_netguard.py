import ipaddress
import re
import socket

import pytest

from odoo.libs import netguard
from odoo.libs.netguard import Scope


class TestClassify:
    @pytest.mark.parametrize(
        ("address", "scope"),
        [
            ("8.8.8.8", Scope.PUBLIC),
            ("2606:4700:4700::1111", Scope.PUBLIC),
            ("10.1.2.3", Scope.PRIVATE),
            ("192.168.0.10", Scope.PRIVATE),
            ("fd00:ec2::254", Scope.PRIVATE),
            ("100.64.0.1", Scope.SHARED),
            ("127.0.0.1", Scope.LOOPBACK),
            ("::1", Scope.LOOPBACK),
            ("169.254.169.254", Scope.LINK_LOCAL),
            ("fe80::1", Scope.LINK_LOCAL),
            ("224.0.0.1", Scope.MULTICAST),
            ("ff02::1", Scope.MULTICAST),
            ("0.0.0.0", Scope.UNSPECIFIED),
            ("::", Scope.UNSPECIFIED),
            ("240.0.0.1", Scope.RESERVED),
            ("198.18.0.1", Scope.RESERVED),
            ("2001:db8::1", Scope.RESERVED),
            ("5f00::1", Scope.RESERVED),
            ("3fff::1", Scope.RESERVED),
        ],
    )
    def test_an_address_is_classified_by_its_range(self, address, scope):
        assert netguard.classify(address) is scope

    @pytest.mark.parametrize(
        ("address", "scope"),
        [
            ("::ffff:127.0.0.1", Scope.LOOPBACK),
            ("::ffff:10.0.0.1", Scope.PRIVATE),
            ("64:ff9b::7f00:1", Scope.LOOPBACK),
            ("64:ff9b:1::a00:1", Scope.PRIVATE),
            ("2002:7f00:1::", Scope.LOOPBACK),
            ("2001:0:4136:e378:8000:63bf:f5ff:fffe", Scope.PRIVATE),
            ("::7f00:1", Scope.RESERVED),
            ("::808:808", Scope.RESERVED),
        ],
    )
    def test_an_ipv6_wrapper_is_classified_by_the_ipv4_address_it_carries(
        self, address, scope
    ):
        assert netguard.classify(address) is scope

    def test_an_address_object_is_accepted(self):
        assert netguard.classify(ipaddress.ip_address("8.8.4.4")) is Scope.PUBLIC


def resolver_for(mapping):
    def resolve(host, port, *args, **kwargs):
        if host not in mapping:
            raise socket.gaierror(socket.EAI_NONAME, "no such host")
        family = socket.AF_INET
        return [
            (
                socket.AF_INET6 if ":" in address else family,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (address, port or 0),
            )
            for address in mapping[host]
        ]

    return resolve


class TestPolicy:
    def test_public_only_permits_only_public_addresses(self):
        policy = netguard.PUBLIC_ONLY
        assert policy.permits("8.8.8.8")
        for address in ("10.0.0.1", "100.64.0.1", "127.0.0.1", "169.254.169.254"):
            assert not policy.permits(address)

    def test_private_allowed_permits_intranet_but_not_multicast_or_unspecified(self):
        policy = netguard.PRIVATE_ALLOWED
        for address in ("8.8.8.8", "10.0.0.1", "100.64.0.1", "127.0.0.1", "fe80::1"):
            assert policy.permits(address)
        for address in ("224.0.0.1", "0.0.0.0", "240.0.0.1"):
            assert not policy.permits(address)

    def test_an_operator_network_widens_a_policy(self):
        policy = netguard.PUBLIC_ONLY.with_networks("10.20.0.0/16")
        assert policy.permits("10.20.3.4")
        assert not policy.permits("10.21.3.4")

    def test_a_malformed_network_is_refused(self):
        with pytest.raises(ValueError):
            netguard.PUBLIC_ONLY.with_networks("not-a-network")


class TestCheckHost:
    def test_a_public_name_yields_its_addresses(self):
        resolver = resolver_for({"example.test": ["93.184.216.34"]})
        addresses = netguard.check_host(
            "example.test", 443, policy=netguard.PUBLIC_ONLY, resolver=resolver
        )
        assert addresses == (ipaddress.ip_address("93.184.216.34"),)

    def test_a_name_that_does_not_resolve_is_refused(self):
        with pytest.raises(netguard.UnresolvableDestination, match="resolve"):
            netguard.check_host(
                "missing.test",
                443,
                policy=netguard.PUBLIC_ONLY,
                resolver=resolver_for({}),
            )

    def test_one_private_address_among_public_ones_refuses_the_name(self):
        resolver = resolver_for({"mixed.test": ["93.184.216.34", "10.0.0.5"]})
        with pytest.raises(netguard.DestinationRefused, match=re.escape("10.0.0.5")):
            netguard.check_host(
                "mixed.test", 443, policy=netguard.PUBLIC_ONLY, resolver=resolver
            )

    def test_a_literal_address_is_checked_without_resolving(self):
        def resolver(*args, **kwargs):
            raise AssertionError("a literal must not be resolved")

        with pytest.raises(netguard.DestinationRefused):
            netguard.check_host(
                "[::1]", 80, policy=netguard.PUBLIC_ONLY, resolver=resolver
            )

    @pytest.mark.parametrize("host", ["2130706433", "0x7f.1", "127.1"])
    def test_a_numeric_spelling_is_judged_by_what_the_system_resolves(self, host):
        with pytest.raises(netguard.DestinationRefused, match=re.escape("127.0.0.1")):
            netguard.check_host(host, 80, policy=netguard.PUBLIC_ONLY)

    @pytest.mark.parametrize("host", ["localhost", "LOCALHOST.", "db.localhost"])
    def test_a_localhost_name_is_loopback_whatever_it_resolves_to(self, host):
        resolver = resolver_for({host: ["93.184.216.34"]})
        with pytest.raises(netguard.DestinationRefused):
            netguard.check_host(
                host, 80, policy=netguard.PUBLIC_ONLY, resolver=resolver
            )


class TestResolve:
    def test_a_literal_is_its_own_address(self):
        assert netguard.resolve("[fe80::1]") == (ipaddress.ip_address("fe80::1"),)

    def test_a_name_yields_each_address_once(self):
        resolver = resolver_for({"twice.test": ["10.0.0.1", "10.0.0.1", "::1"]})
        assert netguard.resolve("Twice.Test.", resolver=resolver) == (
            ipaddress.ip_address("10.0.0.1"),
            ipaddress.ip_address("::1"),
        )

    def test_a_name_that_does_not_resolve_says_so(self):
        with pytest.raises(netguard.UnresolvableDestination):
            netguard.resolve("missing.test", resolver=resolver_for({}))


class TestCheckUrl:
    def test_a_url_yields_its_checked_destination(self):
        resolver = resolver_for({"api.example.test": ["93.184.216.34"]})
        destination = netguard.check_url(
            "https://api.example.test/v1?q=1",
            policy=netguard.PUBLIC_ONLY,
            resolver=resolver,
        )
        assert (destination.scheme, destination.host, destination.port) == (
            "https",
            "api.example.test",
            443,
        )
        assert destination.addresses == (ipaddress.ip_address("93.184.216.34"),)

    @pytest.mark.parametrize(
        "url", ["file:///etc/passwd", "gopher://example.test/", "//example.test/x"]
    )
    def test_a_scheme_other_than_http_is_refused(self, url):
        with pytest.raises(netguard.DestinationRefused, match="scheme"):
            netguard.check_url(url, policy=netguard.PRIVATE_ALLOWED)

    def test_a_url_without_host_is_refused(self):
        with pytest.raises(netguard.DestinationRefused, match="host"):
            netguard.check_url("http:///path", policy=netguard.PRIVATE_ALLOWED)

    def test_a_port_out_of_range_is_refused(self):
        with pytest.raises(netguard.DestinationRefused, match="port"):
            netguard.check_url(
                "http://example.test:99999/", policy=netguard.PUBLIC_ONLY
            )
