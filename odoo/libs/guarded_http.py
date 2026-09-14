from __future__ import annotations

import contextlib
import socket
import threading
import time
import typing

import requests
from requests.adapters import HTTPAdapter
from requests.utils import select_proxy
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
    "GuardedAdapter",
    "GuardedSession",
    "RefusedDestination",
    "ResponseTooLarge",
    "ResponseTooSlow",
    "guarded_session",
]

DEFAULT_TIMEOUT = (10.0, 30.0)
DEFAULT_MAX_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 5

_DEFAULT_PORTS = {"http": 80, "https": 443}


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
        **kwargs: typing.Any,
    ) -> None:
        self.policy = policy
        self.resolver = resolver
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_seconds = max_seconds
        super().__init__(**kwargs)

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
        options = {
            "stream": stream,
            "timeout": self.timeout if timeout is None else timeout,
            "verify": verify,
            "cert": cert,
            "proxies": proxies,
        }
        if select_proxy(request.url or "", proxies):
            response = super().send(request, **options)
        else:
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

    def get_connection_with_tls_context(
        self,
        request: PreparedRequest,
        verify: typing.Any,
        proxies: dict[str, str] | None = None,
        cert: typing.Any = None,
    ) -> typing.Any:
        address = getattr(request, "netguard_address", None)
        if address is None or select_proxy(request.url or "", proxies):
            return super().get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(
            request, verify, cert
        )
        name = host_params["host"]
        host_params["host"] = address
        if host_params.get("scheme") == "https":
            pool_kwargs["assert_hostname"] = name
            pool_kwargs["server_hostname"] = name
        return self.poolmanager.connection_from_host(
            **host_params, pool_kwargs=pool_kwargs
        )

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
        too_slow = ResponseTooSlow(
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
                        raise too_slow
                    yield chunk
            except requests.exceptions.RequestException:
                if watchdog is not None and watchdog.fired.is_set():
                    raise too_slow from None
                raise
            finally:
                if watchdog is not None:
                    watchdog.cancel()
            if watchdog is not None and watchdog.fired.is_set():
                raise too_slow

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
