from __future__ import annotations

import dataclasses
import enum
import ipaddress
import socket
import typing
from urllib.parse import urlsplit

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
    IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network
    Resolver = Callable[..., Sequence[tuple[typing.Any, ...]]]

__all__ = [
    "PRIVATE_ALLOWED",
    "PUBLIC_ONLY",
    "Destination",
    "DestinationRefused",
    "Policy",
    "Scope",
    "UnresolvableDestination",
    "check_address",
    "check_host",
    "check_url",
    "classify",
    "resolve",
]


class Scope(enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    SHARED = "shared"
    LOOPBACK = "loopback"
    LINK_LOCAL = "link_local"
    MULTICAST = "multicast"
    UNSPECIFIED = "unspecified"
    RESERVED = "reserved"


class DestinationRefused(ValueError):
    unresolvable: bool = False


class UnresolvableDestination(DestinationRefused):
    unresolvable = True


_PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "fc00::/7",
        "64:ff9b:1::/48",
    )
)
_SHARED_NETWORK = ipaddress.ip_network("100.64.0.0/10")
_SRV6_SIDS = ipaddress.ip_network("5f00::/16")
_NAT64_WELL_KNOWN = ipaddress.ip_network("64:ff9b::/96")
_IPV4_COMPATIBLE = ipaddress.ip_network("::/96")


def _as_address(address: str | IPAddress) -> IPAddress:
    if isinstance(address, str):
        return ipaddress.ip_address(address.strip("[]"))
    return address


def _unwrap(address: IPAddress) -> IPAddress:
    if isinstance(address, ipaddress.IPv4Address):
        return address
    if address.ipv4_mapped is not None:
        return address.ipv4_mapped
    if address in _NAT64_WELL_KNOWN:
        return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
    if address.sixtofour is not None:
        return address.sixtofour
    if address.teredo is not None:
        return address.teredo[1]
    return address


def classify(address: str | IPAddress) -> Scope:
    ip = _unwrap(_as_address(address))
    if ip.is_unspecified:
        return Scope.UNSPECIFIED
    if ip.is_loopback:
        return Scope.LOOPBACK
    if ip.is_link_local:
        return Scope.LINK_LOCAL
    if ip.is_multicast:
        return Scope.MULTICAST
    if ip in _SHARED_NETWORK:
        return Scope.SHARED
    if any(ip in network for network in _PRIVATE_NETWORKS):
        return Scope.PRIVATE
    if ip.version == 6 and (ip in _IPV4_COMPATIBLE or ip in _SRV6_SIDS):
        return Scope.RESERVED
    if ip.is_global:
        return Scope.PUBLIC
    return Scope.RESERVED


@dataclasses.dataclass(frozen=True, slots=True)
class Policy:
    name: str
    scopes: frozenset[Scope]
    networks: tuple[IPNetwork, ...] = ()

    def permits(self, address: str | IPAddress) -> bool:
        ip = _as_address(address)
        if classify(ip) in self.scopes:
            return True
        unwrapped = _unwrap(ip)
        return any(
            candidate.version == network.version and candidate in network
            for network in self.networks
            for candidate in {ip, unwrapped}
        )

    def with_networks(self, *networks: str | IPNetwork) -> Policy:
        parsed = tuple(ipaddress.ip_network(network) for network in networks)
        return dataclasses.replace(self, networks=self.networks + parsed)


PUBLIC_ONLY = Policy("public_only", frozenset({Scope.PUBLIC}))
PRIVATE_ALLOWED = Policy(
    "private_allowed",
    frozenset(
        {
            Scope.PUBLIC,
            Scope.PRIVATE,
            Scope.SHARED,
            Scope.LOOPBACK,
            Scope.LINK_LOCAL,
        }
    ),
)


@dataclasses.dataclass(frozen=True, slots=True)
class Destination:
    scheme: str
    host: str
    port: int
    addresses: tuple[IPAddress, ...]


def check_address(address: str | IPAddress, *, policy: Policy) -> IPAddress:
    ip = _as_address(address)
    if not policy.permits(ip):
        raise DestinationRefused(
            f"{ip} is a {classify(ip).value} address, "
            f"which the {policy.name} policy refuses"
        )
    return ip


def _literal(host: str) -> IPAddress | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _is_localhost_name(host: str) -> bool:
    return host == "localhost" or host.endswith(".localhost")


def _resolve(host: str, port: int, resolver: Resolver | None) -> Iterable[IPAddress]:
    try:
        infos = (resolver or socket.getaddrinfo)(host, port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError) as error:
        raise UnresolvableDestination(f"{host} does not resolve: {error}") from error
    if not infos:
        raise UnresolvableDestination(f"{host} does not resolve to any address")
    return (ipaddress.ip_address(info[4][0]) for info in infos)


def _normalize(host: str) -> str:
    return host.strip("[]").rstrip(".").lower()


def resolve(
    host: str, port: int = 0, *, resolver: Resolver | None = None
) -> tuple[IPAddress, ...]:
    name = _normalize(host)
    if not name:
        raise UnresolvableDestination("the destination has no host")
    literal = _literal(name)
    if literal is not None:
        return (literal,)
    return tuple(dict.fromkeys(_resolve(name, port, resolver)))


def check_host(
    host: str,
    port: int,
    *,
    policy: Policy,
    resolver: Resolver | None = None,
) -> tuple[IPAddress, ...]:
    name = _normalize(host)
    if not name:
        raise DestinationRefused("the destination has no host")
    if _literal(name) is None and _is_localhost_name(name):
        check_address("127.0.0.1", policy=policy)
    addresses = resolve(name, port, resolver=resolver)
    for address in addresses:
        try:
            check_address(address, policy=policy)
        except DestinationRefused as error:
            if _literal(name) is not None:
                raise
            raise DestinationRefused(f"{host} resolves to {error}") from None
    return addresses


_DEFAULT_PORTS = {"http": 80, "https": 443}


def check_url(
    url: str,
    *,
    policy: Policy,
    resolver: Resolver | None = None,
) -> Destination:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS:
        raise DestinationRefused(
            f"the scheme {scheme or '(none)'!r} is not http or https"
        )
    if not parts.hostname:
        raise DestinationRefused(f"{url!r} has no host")
    try:
        port = parts.port or _DEFAULT_PORTS[scheme]
    except ValueError as error:
        raise DestinationRefused(f"{url!r} has an invalid port: {error}") from error
    addresses = check_host(parts.hostname, port, policy=policy, resolver=resolver)
    return Destination(scheme, parts.hostname, port, addresses)
