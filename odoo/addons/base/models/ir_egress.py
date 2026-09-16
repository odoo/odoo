import logging
from typing import Any, Literal
from urllib.parse import urlsplit

import requests

from odoo import api, models
from odoo.libs import guarded_http, netguard
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

PolicyName = Literal["public", "private"]

_POLICIES: dict[str, netguard.Policy] = {
    "public": netguard.PUBLIC_ONLY,
    "private": netguard.PRIVATE_ALLOWED,
}

ALLOWED_NETWORKS_PARAM = "base.egress_allowed_networks"


class IrEgress(models.AbstractModel):
    _name = "ir.egress"
    _description = "Outbound HTTP"

    @api.model
    def _get_policy(self, policy: PolicyName = "public") -> netguard.Policy:
        base = _POLICIES[policy]
        configured = (
            self.env["ir.config_parameter"].sudo().get_param(ALLOWED_NETWORKS_PARAM)
            or ""
        )
        networks = configured.replace(",", " ").split()
        _debug.logic("egress_policy", policy=policy, extra_networks=len(networks))
        try:
            return base.with_networks(*networks)
        except ValueError:
            _debug.logic("egress_networks_ignored", policy=policy, reason="malformed")
            _logger.error(
                "Ignoring the system parameter %s: %r is not a list of networks, "
                "so no extra network is allowed",
                ALLOWED_NETWORKS_PARAM,
                configured,
            )
            return base

    @api.private
    @api.model
    def check_url(
        self, url: str, *, policy: PolicyName = "public"
    ) -> netguard.Destination:
        destination = netguard.check_url(url, policy=self._get_policy(policy))
        _debug.logic("egress_url_allowed", policy=policy, host=urlsplit(url).hostname)
        return destination

    @api.private
    @api.model
    def session(
        self,
        *,
        purpose: str,
        policy: PolicyName = "public",
        timeout: float | tuple[float, float] = guarded_http.DEFAULT_TIMEOUT,
        max_bytes: int | None = guarded_http.DEFAULT_MAX_BYTES,
        max_seconds: float | None = None,
        max_redirects: int = guarded_http.DEFAULT_MAX_REDIRECTS,
        session_class: type[guarded_http.GuardedSession] = guarded_http.GuardedSession,
        **adapter_options: Any,
    ) -> guarded_http.GuardedSession:
        session = guarded_http.guarded_session(
            self._get_policy(policy),
            timeout=timeout,
            max_bytes=max_bytes,
            max_seconds=max_seconds,
            max_redirects=max_redirects,
            session_class=session_class,
            **adapter_options,
        )
        self._prepare_session(session, purpose=purpose, policy=policy)
        _debug.lifecycle(
            "egress_session",
            purpose=purpose,
            policy=policy,
            max_bytes=max_bytes,
            max_redirects=max_redirects,
        )
        return session

    @api.model
    def _prepare_session(
        self, session: requests.Session, *, purpose: str, policy: PolicyName
    ) -> None:
        def trace(response: requests.Response, *args: Any, **kwargs: Any) -> None:
            if _debug.pipeline.enabled:
                _debug.pipeline(
                    "egress_response",
                    purpose=purpose,
                    policy=policy,
                    host=urlsplit(response.url).hostname,
                    status=response.status_code,
                )

        session.hooks["response"].append(trace)

    @api.private
    @api.model
    def request(
        self,
        method: str,
        url: str,
        *,
        purpose: str,
        policy: PolicyName = "public",
        max_bytes: int | None = guarded_http.DEFAULT_MAX_BYTES,
        max_seconds: float | None = None,
        max_redirects: int = guarded_http.DEFAULT_MAX_REDIRECTS,
        **kwargs: Any,
    ) -> requests.Response:
        session = self.session(
            purpose=purpose,
            policy=policy,
            max_bytes=max_bytes,
            max_seconds=max_seconds,
            max_redirects=max_redirects,
        )
        if kwargs.get("stream"):
            _debug.pipeline(
                "egress_request", purpose=purpose, method=method, streamed=True
            )
            return session.request(method, url, **kwargs)
        with _debug.perf("egress_request", purpose=purpose, method=method):
            with session:
                return session.request(method, url, **kwargs)
