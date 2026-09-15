import ipaddress
import itertools
import json
import logging
import random
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

import requests
from requests.auth import HTTPDigestAuth
from urllib3.exceptions import ReadTimeoutError
from urllib3.util.retry import Retry

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.libs import netguard, redact
from odoo.libs.guarded_http import GuardedSession

from .exceptions import (
    AuthenticationError,
    ClientError,
    CommError,
    CommTimeoutError,
    HostNotAllowedError,
    RateLimitError,
    ServerError,
)
from .exchange_queue import queue_exchange_values
from .payload import split_large_payload
from .session_cache import (
    get_session_cache,
)

_logger = logging.getLogger(__name__)

register_url_secret = redact.register_pattern


class _ShapedRetry(Retry):
    """`Retry` with a `fixed` and a `linear` backoff, neither of which
    `urllib3` has: its own `get_backoff_time()` is hardcoded to exponential
    (`backoff_factor * 2 ** (n - 1)`), so `retry_backoff_type="fixed"` and
    `"linear"` used to fall back to that same formula and be indistinguishable
    from `"exponential"`.

    `backoff_type` lives outside `Retry.__init__`'s own fields because
    `Retry.new()` clones a retry object with `type(self)(**params)` using only
    those fields; it is instead carried as a plain attribute and copied across
    by the `new()` override below, so a clone made mid-retry keeps its shape.
    """

    backoff_type = "exponential"
    retry_after_cap = None

    def new(self, **kw):
        clone = super().new(**kw)
        clone.backoff_type = self.backoff_type
        clone.retry_after_cap = self.retry_after_cap
        return clone

    def is_retry(self, method, status_code, has_retry_after=False):
        # A 429 means the vendor refused the request without acting on it, so
        # resending is safe even for a POST; any other status after a POST may
        # follow a charge, a stamp or a message already sent.
        if status_code == 429 and not self._is_method_retryable(method):
            return bool(self.total)
        return super().is_retry(method, status_code, has_retry_after)

    def get_retry_after(self, response):
        retry_after = super().get_retry_after(response)
        if retry_after is None or not self.retry_after_cap:
            return retry_after
        return min(retry_after, self.retry_after_cap)

    def get_backoff_time(self):
        if self.backoff_type == "exponential":
            return super().get_backoff_time()

        # Same "ignore redirects" rule as Retry.get_backoff_time().
        consecutive_errors_len = len(
            list(
                itertools.takewhile(
                    lambda x: x.redirect_location is None,
                    reversed(self.history),
                ),
            ),
        )
        if consecutive_errors_len <= 1:
            return 0

        if self.backoff_type == "fixed":
            backoff_value = self.backoff_factor
        else:
            backoff_value = self.backoff_factor * (consecutive_errors_len - 1)
        if self.backoff_jitter > 0.0:
            backoff_value += random.random() * self.backoff_jitter
        return float(max(0, min(self.backoff_max, backoff_value)))


_MAX_LOGGED_PAYLOAD = 10000


def _error_type_for_status(status_code):
    if status_code == 401:
        return "auth"
    if status_code == 429:
        return "rate_limit"
    if 400 <= status_code < 500:
        return "validation"
    return "server"


_PRIVATE_SUFFIXES = (".local", ".lan", ".internal", ".home")

_PRIVATE_SCOPES = frozenset(
    {netguard.Scope.PRIVATE, netguard.Scope.LOOPBACK, netguard.Scope.LINK_LOCAL}
)


def is_private_host(host):
    if not host:
        return False
    host = host.strip("[]").lower()
    try:
        addresses = netguard.resolve(host)
    except netguard.UnresolvableDestination:
        return host == "localhost" or host.endswith(_PRIVATE_SUFFIXES)
    return all(netguard.classify(address) in _PRIVATE_SCOPES for address in addresses)


def _is_exhausted_read_timeout(exc):
    # requests reports a read timeout that outlived its retries as a
    # ConnectionError wrapping urllib3's MaxRetryError, not as a Timeout.
    reason = getattr(exc.args[0], "reason", None) if exc.args else None
    return isinstance(reason, ReadTimeoutError)


def _masked_cause(exc: BaseException) -> BaseException:
    masked = tuple(
        redact.mask_text(arg) if isinstance(arg, str) else arg for arg in exc.args
    )
    if masked != exc.args:
        exc.args = masked
    return exc


class _CredentialSession(GuardedSession):
    # requests strips only Authorization on a cross-host redirect; a vendor key
    # in X-API-Key or a custom header would follow the redirect to the new host.
    credential_header_names = frozenset()

    def rebuild_auth(self, prepared_request, response):
        super().rebuild_auth(prepared_request, response)
        if not self.credential_header_names:
            return
        if not self.should_strip_auth(response.request.url, prepared_request.url):
            return
        for name in list(prepared_request.headers):
            if name.lower() in self.credential_header_names:
                del prepared_request.headers[name]


class OutboundAPIClient:
    def __init__(
        self,
        env,
        endpoint_code,
        company_id=None,
        credential_id=None,
        egress_policy="private",
        connection_id=None,
    ):
        self.env = env
        self.egress_policy = egress_policy
        self.endpoint_code = endpoint_code
        self.company_id = company_id or env.company.id
        self.user_id = env.user.id
        self._credential_header_names = frozenset()
        self._credential_auth_applied = False

        self.service = (
            env["integration.service"]
            .sudo()
            .search(
                [
                    ("code", "=", endpoint_code),
                    ("active", "=", True),
                ],
                limit=1,
            )
        )

        if not self.service:
            raise CommError(
                _("API service '%s' not found or inactive") % endpoint_code,
            )

        connections = env["integration.connection"]
        if connection_id:
            self.connection = connections.sudo().browse(connection_id)
            if (
                not self.connection.exists()
                or not self.connection.active
                or self.connection.service_id != self.service
            ):
                raise CommError(
                    _(
                        "Connection %(connection)s is not an active connection of "
                        "service '%(service)s'",
                        connection=connection_id,
                        service=endpoint_code,
                    )
                )
            self.credential = self.connection.credential_id
            if self.credential and not self.credential.active:
                raise CommError(_("Invalid or inactive credential"))
        elif credential_id:
            self.credential = env["credential.credential"].sudo().browse(credential_id)
            if not self.credential.exists() or not self.credential.active:
                raise CommError(_("Invalid or inactive credential"))
            self.connection = connections._for_credential(self.service, self.credential)
        else:
            self.connection = connections._resolve(
                self.service, company=self.company_id, user=self.user_id
            )
            self.credential = self.connection.credential_id

        if not self.credential and self.service.auth_type != "none":
            if self.service.per_record_connections and not self.connection:
                raise CommError(
                    _(
                        "Service '%s' connects each record on its own connection; "
                        "the call must name one",
                        endpoint_code,
                    ),
                )
            raise CommError(
                _(
                    "No active credentials for service '%(service)s' and company ID "
                    "%(company)s in its %(environment)s environment",
                    service=endpoint_code,
                    company=self.company_id,
                    environment=self.service.environment,
                ),
            )

        if self.credential.is_expired:
            raise CommError(
                _("Credentials have expired on %s") % self.credential.date_expiration,
            )

        self._credential_usable = bool(self.credential) and (
            self.connection.credential_id == self.credential
        )
        if self.credential and not self._credential_usable:
            _logger.warning(
                "Credential %s has no connection to service '%s' and will not "
                "authenticate its calls; the request is sent without its secret.",
                self.credential.id,
                endpoint_code,
            )

        self.session = self._get_or_create_session()

        if self.connection:
            self.environment = self.connection.environment
            self.base_url = self.connection._base_url() or ""
        else:
            self.environment = self.service.environment
            if self.environment == "production":
                self.base_url = self.service.endpoint_url or ""
            else:
                self.base_url = (
                    self.service.endpoint_url_test or self.service.endpoint_url or ""
                )

        _logger.info(
            "OutboundAPIClient initialized: service=%s, company=%s, environment=%s",
            endpoint_code,
            self.company_id,
            self.environment,
        )

    def _get_or_create_session(self):
        cache = get_session_cache(self.env)
        cache_key = (
            f"{self.endpoint_code}:{self.company_id}:{self.credential.credential_hash}"
            f":{self.egress_policy}"
        )

        session = cache.get(cache_key)

        if session is None:
            session = self._create_session()
            cache.set(cache_key, session)

        return session

    def _create_session(self):
        session = self.env["ir.egress"].session(
            purpose=f"integration:{self.endpoint_code}",
            policy=self.egress_policy,
            max_bytes=None,
            max_redirects=requests.models.DEFAULT_REDIRECT_LIMIT,
            session_class=_CredentialSession,
            pool_connections=10,
            pool_maxsize=50,
            max_retries=(self._get_retry_config() if self.service.retry_enabled else 0),
        )

        session.headers.update(
            {
                "User-Agent": f"Odoo-API-Transport/1.0 ({self.endpoint_code})",
                "Accept": "application/json",
            },
        )

        _logger.debug("Created new session for %s", self.endpoint_code)

        return session

    def _get_retry_config(self):
        if not self.service.retry_enabled:
            return None

        backoff_type = self.service.retry_backoff_type
        backoff_factor = {
            "fixed": 1.0,
            "linear": 1.0,
            "exponential": 2.0,
        }.get(backoff_type, 2.0)

        retry = _ShapedRetry(
            total=self.service.retry_max_attempts or 3,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=Retry.DEFAULT_ALLOWED_METHODS,
            raise_on_status=False,
        )
        retry.backoff_type = backoff_type or "exponential"
        retry.retry_after_cap = self.service.timeout_read or 30
        return retry

    def request(self, method, endpoint, raw=False, **kwargs):
        method = method.upper()
        trace_id = kwargs.pop("trace_id", str(uuid.uuid4()))
        skip_cache = kwargs.pop("skip_cache", False)
        skip_rate_limit = kwargs.pop("skip_rate_limit", False)
        skip_logging = kwargs.pop("skip_logging", False)
        raise_for_status = kwargs.pop("raise_for_status", True)

        url = self._get_url(endpoint)

        if (
            method == "GET"
            and not skip_cache
            and not raw
            and self.service.cache_enabled
        ):
            cached = self._serve_cached(method, url, kwargs, trace_id, skip_logging)
            if cached is not None:
                return cached

        self.service.sudo()._check_before_request(self.company_id)

        if not skip_rate_limit:
            self.check_rate_limit()

        self._update_request_kwargs(url, kwargs)
        self._check_credential_host(url, kwargs)
        self.session.credential_header_names = self._credential_header_names
        start_time = datetime.now()

        try:
            _logger.info("API Request: %s %s", method, redact.mask_url(url))
            response = self.session.request(
                method=method,
                url=url,
                **kwargs,
            )

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

            if raise_for_status:
                response.raise_for_status()

            return self._deliver(
                response, elapsed_ms, raw, method, url, kwargs, trace_id, skip_logging
            )

        except requests.exceptions.Timeout as e:
            error = redact.mask_text(str(e))
            _logger.error("API Timeout: %s - %s", redact.mask_url(url), error)
            self._record_failure(
                method, url, kwargs, trace_id, skip_logging, error, "timeout"
            )
            raise CommTimeoutError(
                _("Request timed out: %s") % redact.mask_url(url)
            ) from _masked_cause(e)

        except requests.exceptions.HTTPError as e:
            error = redact.mask_text(self._extract_error(e.response))
            _logger.error("API HTTP Error: %s - %s", redact.mask_url(url), error)
            status_code = e.response.status_code
            self._record_failure(
                method,
                url,
                kwargs,
                trace_id,
                skip_logging,
                error,
                _error_type_for_status(status_code),
                payload={
                    "status_code": status_code,
                    "headers": dict(e.response.headers or {}),
                    "body": None,
                },
            )
            raise self._prepare_http_error(status_code, error) from _masked_cause(e)

        except requests.exceptions.RetryError as e:
            error = redact.mask_text(str(e))
            _logger.error("API Retries Exhausted: %s - %s", redact.mask_url(url), error)
            self._record_failure(
                method, url, kwargs, trace_id, skip_logging, error, "server"
            )
            raise ServerError(_("Server error: %s") % error) from _masked_cause(e)

        except requests.exceptions.RequestException as e:
            error = redact.mask_text(str(e))
            if _is_exhausted_read_timeout(e):
                _logger.error("API Timeout: %s - %s", redact.mask_url(url), error)
                self._record_failure(
                    method, url, kwargs, trace_id, skip_logging, error, "timeout"
                )
                raise CommTimeoutError(
                    _("Request timed out: %s") % redact.mask_url(url)
                ) from _masked_cause(e)
            _logger.error("API Request Error: %s - %s", redact.mask_url(url), error)
            self._record_failure(
                method, url, kwargs, trace_id, skip_logging, error, "network"
            )
            raise CommError(_("Request failed: %s") % error) from _masked_cause(e)

        except Exception as e:
            error = redact.mask_text(str(e))
            _logger.exception("Unexpected API error")
            self._record_failure(
                method, url, kwargs, trace_id, skip_logging, error, "other"
            )
            raise CommError(_("Unexpected error: %s") % error) from _masked_cause(e)

    def _update_request_kwargs(self, url, kwargs):
        kwargs["headers"] = self._get_headers(kwargs.pop("headers", {}))

        if "timeout" not in kwargs:
            kwargs["timeout"] = (
                self.service.timeout_connect or 10,
                self.service.timeout_read or 30,
            )
        kwargs.setdefault("verify", self._get_tls_verification(url))
        credential_auth = None if "auth" in kwargs else self._get_auth()
        self._credential_auth_applied = credential_auth is not None
        kwargs.setdefault("auth", credential_auth)

    def _deliver(
        self, response, elapsed_ms, raw, method, url, kwargs, trace_id, skip_logging
    ):
        failed = response.status_code >= 400
        status_error = self._extract_error(response) if failed else None
        status_error_type = (
            _error_type_for_status(response.status_code) if failed else None
        )

        if raw:
            self._track_usage(not failed)
            if not skip_logging:
                self._log_request(
                    method,
                    url,
                    kwargs,
                    {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": None,
                        "elapsed_ms": elapsed_ms,
                    },
                    trace_id,
                    error=status_error,
                    error_type=status_error_type,
                )
            return response

        response_data = self._parse_response(response, elapsed_ms)

        if (
            method == "GET"
            and response.status_code == 200
            and self.service.cache_enabled
        ):
            self._store_cached(url, kwargs, response_data)

        self._track_usage(not failed)

        if not skip_logging:
            self._log_request(
                method,
                url,
                kwargs,
                response_data,
                trace_id,
                error=status_error,
                error_type=status_error_type,
            )

        return response_data

    def _serve_cached(self, method, url, kwargs, trace_id, skip_logging):
        try:
            cached = (
                self.env["integration.response.cache"]
                .sudo()
                .get_cached_response(
                    endpoint_code=self.endpoint_code,
                    url=url,
                    params=kwargs.get("params"),
                    company_id=self.company_id,
                    credential_id=self.credential.id,
                )
            )
        except Exception as cache_error:
            _logger.warning(
                "Failed to retrieve from cache, proceeding with API call: %s",
                cache_error,
                exc_info=True,
            )
            self._increment_cache_error()
            return None

        if not cached:
            return None

        if not skip_logging:
            self._log_request(method, url, kwargs, cached, trace_id, cache_hit=True)
        return cached

    def _store_cached(self, url, kwargs, response_data):
        try:
            self.env["integration.response.cache"].sudo().set_cached_response(
                endpoint_code=self.endpoint_code,
                url=url,
                response=response_data,
                params=kwargs.get("params"),
                company_id=self.company_id,
                credential_id=self.credential.id,
            )
        except Exception as cache_error:
            _logger.warning(
                "Failed to save response to cache: %s",
                cache_error,
                exc_info=True,
            )
            self._increment_cache_error()

    def _record_failure(
        self,
        method,
        url,
        kwargs,
        trace_id,
        skip_logging,
        error,
        error_type,
        payload=None,
    ):
        self._track_usage(False)
        if not skip_logging:
            self._log_request(
                method,
                url,
                kwargs,
                payload,
                trace_id,
                error=error,
                error_type=error_type,
            )

    @staticmethod
    def _prepare_http_error(status_code, error):
        if status_code == 401:
            return AuthenticationError(
                _("Authentication failed: %s") % error, status_code
            )
        if status_code == 429:
            return RateLimitError(_("Rate limit exceeded: %s") % error, status_code)
        if 400 <= status_code < 500:
            return ClientError(_("Client error: %s") % error, status_code)
        return ServerError(_("Server error: %s") % error, status_code)

    def get(self, endpoint, **kwargs):
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint, **kwargs):
        return self.request("PUT", endpoint, **kwargs)

    def patch(self, endpoint, **kwargs):
        return self.request("PATCH", endpoint, **kwargs)

    def delete(self, endpoint, **kwargs):
        return self.request("DELETE", endpoint, **kwargs)

    def post_bulk(self, endpoint, items, max_payload_size=None, **kwargs):
        if not isinstance(items, list):
            raise ClientError("post_bulk requires a list of items")

        max_size = max_payload_size or (1024 * 1024)

        chunks = split_large_payload(items, max_size=max_size)

        if len(chunks) > 1:
            _logger.info(
                "Payload split into %d chunks for %s (max size: %d bytes)",
                len(chunks),
                endpoint,
                max_size,
            )

        responses = []
        for i, chunk in enumerate(chunks, 1):
            _logger.debug(
                "Sending chunk %d/%d with %d items to %s",
                i,
                len(chunks),
                len(chunk) if isinstance(chunk, list) else 1,
                endpoint,
            )

            chunk_kwargs = kwargs.copy()
            chunk_kwargs["json"] = chunk

            response = self.post(endpoint, **chunk_kwargs)
            responses.append(response)

        return responses

    def _get_url(self, endpoint):
        if endpoint.startswith(("http://", "https://")):
            return endpoint

        try:
            parsed = urlparse(self.base_url)

            if parsed.scheme not in ("http", "https"):
                raise ValueError(
                    f"Invalid URL scheme '{parsed.scheme}' for service '{self.endpoint_code}'. "
                    f"Expected 'http' or 'https'.",
                )

            if not parsed.netloc:
                raise ValueError(
                    f"Missing hostname in base URL for service '{self.endpoint_code}': {self.base_url}"
                )

            if parsed.port is not None:
                if not (0 < parsed.port <= 65535):
                    raise ValueError(
                        f"Invalid port {parsed.port} in base URL for service '{self.endpoint_code}'. "
                        f"Port must be between 1 and 65535.",
                    )

            hostname = parsed.hostname or parsed.netloc.split(":")[0]
            if hostname not in ("localhost", "127.0.0.1"):
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", hostname):
                    try:
                        ipaddress.ip_address(hostname)
                    except ValueError as e:
                        raise ValueError(
                            f"Invalid IP address '{hostname}' in base URL for service '{self.endpoint_code}': {e}",
                        ) from e

        except ValueError as e:
            raise ValueError(
                f"Invalid base URL format for service '{self.endpoint_code}': {self.base_url}\n"
                f"Error: {e}\n"
                f"Expected format: https://api.example.com or https://api.example.com/v1",
            ) from e

        base = self.base_url.rstrip("/")
        endpoint_normalized = endpoint.lstrip("/")

        if endpoint_normalized:
            full_url = f"{base}/{endpoint_normalized}"
        else:
            full_url = base

        _logger.debug(
            "Built URL: %s (base: %s, endpoint: %s)",
            full_url,
            self.base_url,
            endpoint,
        )

        return full_url

    def _check_credential_host(self, url, kwargs):
        if not (self._credential_header_names or self._credential_auth_applied):
            return
        host = urlparse(url).hostname or ""
        allowed = (
            self.connection._is_credential_host_allowed(host)
            if self.connection
            else self.service._is_credential_host_allowed(host)
        )
        if allowed:
            return
        _logger.error(
            "Refused to send the credential of service '%s' to '%s': the host is "
            "neither the endpoint's own nor listed in its allowed hosts.",
            self.endpoint_code,
            host,
        )
        raise HostNotAllowedError(
            _(
                "Refusing to send the credential of service '%(service)s' to "
                "'%(host)s'. Add the host to the endpoint's Allowed Hosts if it "
                "is meant to receive it.",
            )
            % {"service": self.endpoint_code, "host": host},
        )

    def _get_headers(self, additional_headers=None):
        credential_headers = (
            self.connection._get_auth_headers() if self._credential_usable else {}
        )
        self._credential_header_names = frozenset(
            str(name).lower() for name in credential_headers
        )
        headers = dict(credential_headers)

        if self.service.api_version:
            if self.service.api_version_header:
                headers.setdefault(
                    self.service.api_version_header, self.service.api_version
                )
            if self.service.send_version_headers:
                headers.setdefault("API-Version", self.service.api_version)
                headers.setdefault("X-API-Version", self.service.api_version)

        if additional_headers:
            headers.update(additional_headers)

        return headers

    _HTTP_AUTH_TYPES = ("basic", "digest")

    def _get_auth(self):
        if self.service.auth_type not in self._HTTP_AUTH_TYPES:
            return None
        if not self._credential_usable:
            return None
        pair = self.credential._use_basic_auth("integration:basic_auth")
        if self.service.auth_type == "digest":
            return HTTPDigestAuth(*pair) if pair else None
        return pair

    def _get_tls_verification(self, url):
        if self.service.verify_tls:
            return True
        host = urlparse(url).hostname or ""
        if not is_private_host(host):
            raise UserError(
                _(
                    "Refusing to call '%(host)s' with TLS verification disabled: "
                    "it is not a private-network host, so the credential for "
                    "service '%(service)s' would be exposed to whoever answers.",
                )
                % {"host": host, "service": self.endpoint_code},
            )
        return False

    def _parse_response(self, response, elapsed_ms):
        try:
            body = response.json()
        except (json.JSONDecodeError, ValueError) as e:
            _logger.debug("Response is not JSON: %s. Using text content.", e)
            body = response.text

            if not body and response.status_code < 300:
                body = {"status": "ok", "message": "Request successful"}

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
            "text": response.text,
            "elapsed_ms": elapsed_ms,
            "from_cache": False,
        }

    def _extract_error(self, response):
        try:
            error_data = response.json()
            for field in ["error", "message", "error_description", "detail"]:
                if field in error_data:
                    error_value = error_data[field]
                    if isinstance(error_value, dict) and "message" in error_value:
                        return error_value["message"]
                    return str(error_value)
            return json.dumps(error_data)
        except Exception as e:
            _logger.debug("Could not extract error from JSON: %s", e)
            return response.text[:500]

    def _increment_cache_error(self):
        try:
            self.service.sudo().write(
                {
                    "cache_error_count": self.service.cache_error_count + 1,
                    "cache_last_error": fields.Datetime.now(),
                },
            )
        except Exception as e:
            _logger.debug("Failed to increment cache error counter: %s", e)

    def log_external_exchange(
        self,
        method,
        url,
        *,
        request_body=None,
        status_code=None,
        elapsed_ms=0,
        error=None,
        trace_id=None,
    ):
        failed = bool(error) or (status_code is not None and status_code >= 400)
        if failed and not error:
            error = f"HTTP {status_code}"
        self._track_usage(not failed)
        response_data = {
            "status_code": status_code or 0,
            "headers": {},
            "body": None,
            "elapsed_ms": elapsed_ms,
        }
        self._log_request(
            method,
            url,
            {"data": request_body} if request_body is not None else {},
            response_data,
            trace_id or str(uuid.uuid4()),
            error=error,
            error_type=(
                _error_type_for_status(status_code)
                if status_code and status_code >= 400
                else ("network" if error else None)
            ),
        )

    def check_rate_limit(self):
        if not self.service.check_rate_limit(company_id=self.company_id):
            raise RateLimitError(
                _("Rate limit exceeded for service '%s'. Please try again later.")
                % self.endpoint_code,
            )

    def _log_request(
        self,
        method,
        url,
        request_kwargs,
        response_data,
        trace_id,
        cache_hit=False,
        error=None,
        error_type=None,
    ):
        try:
            self._queue_event_log(
                method,
                url,
                request_kwargs,
                response_data,
                trace_id,
                cache_hit=cache_hit,
                error=error,
                error_type=error_type,
            )
        except Exception:
            _logger.exception(
                "Could not record an integration.exchange row for %s %s (trace %s); "
                "the exchange itself is unaffected.",
                method,
                redact.mask_url(url),
                trace_id,
            )

    def _track_usage(self, success):
        if not self.credential:
            return
        try:
            self.credential.increment_usage(success=success)
        except Exception:
            _logger.exception(
                "Could not record credential usage for service '%s'; "
                "the exchange itself is unaffected.",
                self.endpoint_code,
            )

    def _serialize_payload_for_log(self, body):
        if not body:
            return ""

        if not self.service.log_request_payload:
            return "<suppressed by service configuration>"

        if isinstance(body, (bytes, bytearray)):
            try:
                body = body.decode("utf-8")
            except UnicodeDecodeError:
                return f"<{len(body)} bytes, binary, not logged>"

        if isinstance(body, str):
            length = len(body)
            try:
                body = json.loads(body)
            except ValueError:
                return f"<{length} chars, unparseable, not logged>"
            if not isinstance(body, (dict, list)):
                return f"<{length} chars, unparseable, not logged>"

        if not isinstance(body, (dict, list)):
            return f"<{type(body).__name__}, not logged>"

        return json.dumps(redact.mask_data(body))[:_MAX_LOGGED_PAYLOAD]

    EVENT_LOG_ANNOTATIONS_KEY = "integration_exchange_annotations"
    _ANNOTATION_FIELDS = ("tags", "origin_model", "origin_record_id")

    def _event_log_annotations(self):
        raw = self.env.context.get(self.EVENT_LOG_ANNOTATIONS_KEY) or {}
        if not isinstance(raw, dict):
            return {}
        return {
            key: value
            for key, value in raw.items()
            if key in self._ANNOTATION_FIELDS and value
        }

    def _queue_event_log(
        self,
        method,
        url,
        request_kwargs,
        response_data,
        trace_id,
        cache_hit=False,
        error=None,
        error_type=None,
    ):

        safe_headers = self._redact_headers(request_kwargs.get("headers"))
        safe_body = self._serialize_payload_for_log(
            request_kwargs.get("json") or request_kwargs.get("data"),
        )

        safe_url = redact.mask_url(url)

        vals = {
            "direction": "outbound",
            "channel_id": f"integration.service,{self.service.id}",
            "company_id": self.company_id,
            "credential_id": self.credential.id,
            "user_id": self.user_id,
            "request_method": method,
            "request_url": safe_url,
            "request_headers": safe_headers,
            "request_payload": safe_body,
            "trace_id": trace_id,
            "cache_hit": cache_hit,
        }

        if response_data:
            safe_response_headers = redact.mask_data(
                response_data.get("headers") or {},
            )
            safe_response_body = redact.mask_data(
                response_data.get("body"),
            )
            status_code = response_data.get("status_code")
            vals.update(
                {
                    "status_code": status_code,
                    "response_headers": safe_response_headers,
                    "response_payload": json.dumps(safe_response_body)[
                        :_MAX_LOGGED_PAYLOAD
                    ],
                    "duration_ms": response_data.get("elapsed_ms", 0),
                    "date_completed": fields.Datetime.now(),
                    "state": "failed" if (status_code or 0) >= 400 else "success",
                },
            )
            if (status_code or 0) >= 400:
                vals["error_type"] = _error_type_for_status(status_code)

        if error:
            vals.update(
                {
                    "error_message": redact.mask_text(error),
                    "error_type": error_type,
                    "state": "failed",
                },
            )

        if response_data and not cache_hit:
            vals.update(
                self.service.sudo()._exchange_usage_values(
                    url, request_kwargs, response_data.get("body")
                )
            )

        vals.update(self._event_log_annotations())

        queue_exchange_values(self.env, vals)

    def _redact_headers(self, headers):
        if not isinstance(headers, dict):
            return {}
        by_provenance = {
            key: (
                "***REDACTED***"
                if str(key).lower() in self._credential_header_names
                else value
            )
            for key, value in headers.items()
        }
        return redact.mask_data(by_provenance)

    def probe_health(self):
        """Make an uncached health request without exchange logging.

        A configured health endpoint must return HTTP 200. Otherwise send
        OPTIONS to the root and report success if the request returns. Caught
        request errors return false. Each request uses a five-second timeout.

        :rtype: bool
        """
        try:
            if self.service.health_check_endpoint:
                response = self.get(
                    self.service.health_check_endpoint,
                    skip_cache=True,
                    skip_logging=True,
                    timeout=5,
                )
                return response["status_code"] == 200
            response = self.request(
                "OPTIONS",
                "/",
                skip_cache=True,
                skip_logging=True,
                timeout=5,
            )
            return True
        except Exception as e:
            _logger.debug("Health check failed for %s: %s", self.endpoint_code, e)
            return False


def get_api_client(
    env,
    endpoint_code,
    company_id=None,
    credential_id=None,
    egress_policy="private",
    connection_id=None,
):
    service = (
        env["integration.service"]
        .sudo()
        .search(
            [
                ("code", "=", endpoint_code),
                ("active", "=", True),
            ],
            limit=1,
        )
    )

    if not service:
        raise UserError(_("API service '%s' not found or inactive") % endpoint_code)

    return OutboundAPIClient(
        env,
        endpoint_code,
        company_id,
        credential_id,
        egress_policy=egress_policy,
        connection_id=connection_id,
    )
