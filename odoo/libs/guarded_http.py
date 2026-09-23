from __future__ import annotations

import contextlib
import socket
import threading
import time
import typing
import xmlrpc.client

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import MaxRetryError, NewConnectionError
from urllib3.util import parse_url

from odoo.libs import netguard

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from requests.models import PreparedRequest, Response

    from odoo.libs.netguard import IPAddress, Policy, Resolver

__all__ = [
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_REDIRECTS",
    "DEFAULT_TIMEOUT",
    "ENVIRONMENT_PROXY_VARIABLES",
    "GuardedAdapter",
    "GuardedSession",
    "RefusedDestination",
    "ResponseTooLarge",
    "ResponseTooSlow",
    "configure_egress_proxy",
    "egress_proxy",
    "guarded_session",
]

DEFAULT_TIMEOUT = (10.0, 30.0)
DEFAULT_MAX_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 5

_DEFAULT_PORTS = {"http": 80, "https": 443}

# The proxy variables requests would read from the environment. A guarded
# session never does: a proxy resolves the name again, after the check, so it
# is declared once for the process and reached with the checked address.
ENVIRONMENT_PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

_egress_proxy: str | None = None


def configure_egress_proxy(url: str | None) -> None:
    global _egress_proxy  # noqa: PLW0603 one process-wide egress route
    if url:
        parts = parse_url(url)
        if parts.scheme not in ("http", "https") or not parts.host:
            raise ValueError(
                f"the egress proxy must be an http:// or https:// URL, got {url!r}"
            )
    _egress_proxy = url or None


def egress_proxy() -> str | None:
    return _egress_proxy


class _Configured:
    pass


_CONFIGURED = _Configured()


class RefusedDestination(requests.exceptions.InvalidURL, netguard.DestinationRefused):
    def __init__(self, *args: object, request: PreparedRequest | None = None) -> None:
        # the request keyword requests' base reads and ValueError's ignores
        requests.exceptions.RequestException.__init__(self, *args, request=request)


class ResponseTooLarge(requests.exceptions.RequestException):
    pass


class ResponseTooSlow(requests.exceptions.Timeout):
    pass


def _failed_to_connect(error: requests.exceptions.ConnectionError) -> bool:
    cause = error.args[0] if error.args else None
    return isinstance(cause, MaxRetryError) and isinstance(
        cause.reason, NewConnectionError
    )


class GuardedAdapter(HTTPAdapter):
    def __init__(
        self,
        policy: Policy,
        *,
        resolver: Resolver | None = None,
        timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
        max_bytes: int | None = DEFAULT_MAX_BYTES,
        max_seconds: float | None = None,
        proxy: str | _Configured | None = _CONFIGURED,
        **kwargs: typing.Any,
    ) -> None:
        self.policy = policy
        self.resolver = resolver
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_seconds = max_seconds
        self._proxy = proxy
        super().__init__(**kwargs)

    @property
    def proxy(self) -> str | None:
        if isinstance(self._proxy, _Configured):
            return _egress_proxy
        return self._proxy

    @typing.override
    def send(  # type: ignore[override]
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: typing.Any = None,
        verify: typing.Any = True,
        cert: typing.Any = None,
        proxies: dict[str, str] | None = None,
    ) -> Response:
        started = time.monotonic()
        addresses = request.__dict__.pop("netguard_addresses", None)
        if addresses is None:
            addresses = self._check(request)
        # the route is the adapter's own: whatever proxies requests merged in
        # (the environment's, a caller's) would re-resolve the checked name
        del proxies
        options = {
            "stream": stream,
            "timeout": self.timeout if timeout is None else timeout,
            "verify": verify,
            "cert": cert,
            "proxies": {},
        }
        response = self._send_pinned(request, addresses, options)
        return self._capped(response, started)

    def _check(self, request: PreparedRequest) -> tuple[IPAddress, ...]:
        parts = parse_url(request.url or "")
        scheme = (parts.scheme or "").lower()
        if scheme not in _DEFAULT_PORTS:
            raise RefusedDestination(
                f"the scheme {scheme or '(none)'!r} is not http or https",
                request=request,
            )
        try:
            return netguard.check_host(
                parts.host or "",
                parts.port or _DEFAULT_PORTS[scheme],
                policy=self.policy,
                resolver=self.resolver,
            )
        except netguard.DestinationRefused as error:
            refusal = RefusedDestination(str(error), request=request)
            refusal.unresolvable = error.unresolvable
            raise refusal from None

    def _send_pinned(
        self,
        request: PreparedRequest,
        addresses: tuple[IPAddress, ...],
        options: dict[str, typing.Any],
    ) -> Response:
        added_host = "Host" not in request.headers
        if added_host:
            request.headers["Host"] = parse_url(request.url or "").netloc or ""
        try:
            for position, address in enumerate(addresses, start=1):
                request.netguard_address = str(address)  # type: ignore[attr-defined]
                try:
                    return super().send(request, **options)
                except requests.exceptions.ConnectionError as error:
                    if position == len(addresses) or not _failed_to_connect(error):
                        raise
            raise AssertionError("check_host returns at least one address")
        finally:
            del request.netguard_address  # type: ignore[attr-defined]
            if added_host:
                del request.headers["Host"]

    @typing.override
    def get_connection_with_tls_context(
        self,
        request: PreparedRequest,
        verify: typing.Any,
        proxies: dict[str, str] | None = None,
        cert: typing.Any = None,
    ) -> typing.Any:
        del proxies
        address = getattr(request, "netguard_address", None)
        if address is None:
            return super().get_connection_with_tls_context(
                request, verify, proxies={}, cert=cert
            )
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(
            request, verify, cert
        )
        name = host_params["host"]
        host_params["host"] = address
        if host_params.get("scheme") == "https":
            pool_kwargs["assert_hostname"] = name
            pool_kwargs["server_hostname"] = name
        # through a proxy the checked address is still the destination: a
        # CONNECT to it for https, an absolute-form request line naming it for
        # http (request_url), with TLS and the Host header on the name
        manager = self.proxy_manager_for(self.proxy) if self.proxy else self.poolmanager
        return manager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)

    def request_url(self, request: PreparedRequest, proxies: typing.Any) -> str:
        del proxies
        address = getattr(request, "netguard_address", None)
        parts = parse_url(request.url or "")
        if address is None or not self.proxy or parts.scheme != "http":
            return super().request_url(request, {})
        host = f"[{address}]" if ":" in str(address) else str(address)
        port = parts.port or _DEFAULT_PORTS["http"]
        return f"http://{host}:{port}{request.path_url}"

    def _capped(self, response: Response, started: float) -> Response:
        limit = self.max_bytes
        deadline = None if self.max_seconds is None else started + self.max_seconds
        announced = response.headers.get("Content-Length", "")
        if (
            limit is not None
            and response.request.method != "HEAD"
            and announced.isdigit()
            and int(announced) > limit
        ):
            response.close()
            raise ResponseTooLarge(
                f"the response announces {announced} bytes, over the {limit} cap",
                response=response,
            )
        iter_content: Callable[..., Iterator[typing.Any]] = response.iter_content

        def too_slow() -> ResponseTooSlow:
            return ResponseTooSlow(
                f"the response took longer than {self.max_seconds}s", response=response
            )

        def capped(
            chunk_size: int | None = 1, decode_unicode: bool = False
        ) -> Iterator[typing.Any]:
            received = 0
            watchdog = _start_watchdog(response, deadline)
            try:
                for chunk in iter_content(chunk_size, decode_unicode):
                    received += len(chunk)
                    if limit is not None and received > limit:
                        response.close()
                        raise ResponseTooLarge(
                            f"the response exceeds the {limit} byte cap",
                            response=response,
                        )
                    if watchdog is not None and watchdog.fired.is_set():
                        raise too_slow()
                    yield chunk
            except requests.exceptions.RequestException:
                if watchdog is not None and watchdog.fired.is_set():
                    raise too_slow() from None
                raise
            finally:
                if watchdog is not None:
                    watchdog.cancel()
            if watchdog is not None and watchdog.fired.is_set():
                raise too_slow()

        response.iter_content = capped  # type: ignore[method-assign]
        return response


def _socket_of(response: Response) -> socket.socket | None:
    sock = getattr(getattr(response.raw, "connection", None), "sock", None)
    if sock is not None:
        return sock
    reader = getattr(getattr(response.raw, "_fp", None), "fp", None)
    return getattr(getattr(reader, "raw", None), "_sock", None)


class _Watchdog(threading.Timer):
    fired: threading.Event


def _start_watchdog(response: Response, deadline: float | None) -> _Watchdog | None:
    if deadline is None:
        return None
    fired = threading.Event()

    def expire() -> None:
        fired.set()
        sock = _socket_of(response)
        if sock is not None:
            with contextlib.suppress(OSError):
                sock.shutdown(socket.SHUT_RDWR)

    watchdog = _Watchdog(max(deadline - time.monotonic(), 0.0), expire)
    watchdog.fired = fired
    watchdog.daemon = True
    watchdog.start()
    return watchdog


class GuardedSession(requests.Session):
    @typing.override
    def merge_environment_settings(  # type: ignore[override]
        self,
        url: str | None,
        proxies: typing.Any,
        stream: typing.Any,
        verify: typing.Any,
        cert: typing.Any,
    ) -> dict[str, typing.Any]:
        # the environment still names the CA bundle and netrc, never a proxy
        settings = super().merge_environment_settings(
            url, proxies, stream, verify, cert
        )
        settings["proxies"] = {}
        return settings

    @typing.override
    def send(self, request: PreparedRequest, **kwargs: typing.Any) -> Response:  # type: ignore[override]
        adapter = self.get_adapter(url=request.url or "")
        if isinstance(adapter, GuardedAdapter):
            request.netguard_addresses = adapter._check(request)  # type: ignore[attr-defined]
        return super().send(request, **kwargs)


def guarded_session(
    policy: Policy,
    *,
    resolver: Resolver | None = None,
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
    max_bytes: int | None = DEFAULT_MAX_BYTES,
    max_seconds: float | None = None,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    session_class: type[GuardedSession] = GuardedSession,
    **adapter_options: typing.Any,
) -> GuardedSession:
    adapter = GuardedAdapter(
        policy,
        resolver=resolver,
        timeout=timeout,
        max_bytes=max_bytes,
        max_seconds=max_seconds,
        **adapter_options,
    )
    session = session_class()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.max_redirects = max_redirects
    return session


class GuardedXmlRpcTransport(xmlrpc.client.Transport):
    def __init__(
        self,
        session: requests.Session,
        base_url: str,
        *,
        timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__()
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def request(  # type: ignore[override]
        self,
        host: str,
        handler: str,
        request_body: bytes,
        verbose: bool = False,
    ) -> typing.Any:
        # `host` is the URL's netloc as ServerProxy parsed it; the base URL
        # given at construction carries the scheme too, so it is the one used
        # to send. The netloc still carries the URL's userinfo, which stdlib
        # turns into a Basic Authorization header.
        _, auth_headers, _ = self.get_host_info(host)
        url = f"{self._base_url}{handler}"
        response = self._session.post(
            url,
            data=request_body,
            headers={"Content-Type": "text/xml", **dict(auth_headers or ())},
            timeout=self._timeout,
        )
        if not response.ok:
            raise xmlrpc.client.ProtocolError(
                url, response.status_code, response.reason, dict(response.headers)
            )
        del verbose
        parser, unmarshaller = self.getparser()
        parser.feed(response.content)
        parser.close()
        return unmarshaller.close()


def xmlrpc_proxy(
    session: requests.Session,
    url: str,
    *,
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
) -> xmlrpc.client.ServerProxy:
    parts = parse_url(url)
    base_url = f"{parts.scheme}://{parts.netloc}"
    return xmlrpc.client.ServerProxy(
        url,
        transport=GuardedXmlRpcTransport(session, base_url, timeout=timeout),
        allow_none=True,
    )
