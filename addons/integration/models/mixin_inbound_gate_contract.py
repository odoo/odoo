from odoo import api, fields, models

# What the caller must send, in the caller's terms. Each entry is the line a
# person reads on the gate's form and repeats to whoever is integrating.
_SCHEME_SENTENCES = {
    "none": "No credential. The path, the address allow-list and the call "
    "budget are what admit the caller.",
    "bearer": "Authorization: Bearer <token>, or X-Device-Token: <token> for a "
    "caller that cannot set Authorization.",
    "api_key": "Authorization: Bearer <key>.",
    "custom": "A scheme of this receiver's own; see its verifier.",
}


class MixinInboundGate(models.AbstractModel):
    _inherit = "mixin.inbound.gate"

    contract_routes = fields.Text(
        string="Called At",
        compute="_compute_contract",
        help="The routes that reach this gate, as the server serves them.",
    )
    contract_scheme = fields.Text(
        string="Must Send",
        compute="_compute_contract",
        help="What the caller proves itself with.",
    )
    contract_limits = fields.Text(
        string="Held To",
        compute="_compute_contract",
        help="The caps a call is refused for crossing.",
    )
    contract_last_call = fields.Text(
        string="Last Call",
        compute="_compute_contract",
        help="The body of the last call this gate admitted, as it was logged "
        "(masked, and capped at the gate's own payload limit).",
    )

    @api.depends(
        "auth_type",
        "signature_header",
        "signature_prefix",
        "timestamp_verification_enabled",
        "timestamp_header",
        "timestamp_max_age_seconds",
        "ip_whitelist",
        "max_payload_size",
        "rate_limit_enabled",
        "rate_limit_requests",
        "rate_limit_window_seconds",
    )
    def _compute_contract(self):
        routes_by_model = self._inbound_routes_by_model()
        for gate in self:
            gate.contract_routes = "\n".join(gate._contract_routes(routes_by_model))
            gate.contract_scheme = gate._contract_scheme()
            gate.contract_limits = "\n".join(gate._contract_limits())
            gate.contract_last_call = gate._contract_last_call()

    @api.model
    def _inbound_routes_by_model(self) -> dict[str, list[str]]:
        """Which rules name which model in their ``receiver=``.

        Read from the routing map, so a route that stopped existing stops
        being promised and a new one appears without anyone editing a text
        field.
        """
        routes: dict[str, list[str]] = {}
        try:
            routing_map = self.env["ir.http"].routing_map()
        except Exception:  # a contract is never worth a traceback
            return routes
        for rule in routing_map.iter_rules():
            routing = getattr(rule.endpoint, "routing", {})
            receiver = routing.get("receiver")
            if not receiver:
                continue
            model_name = receiver.partition(":")[0]
            methods = sorted((rule.methods or set()) - {"HEAD", "OPTIONS"}) or [
                "GET",
                "POST",
            ]
            routes.setdefault(model_name, []).append(
                f"{', '.join(methods)} {rule.rule}"
            )
        return routes

    def _contract_models(self) -> list[str]:
        """The models a route may name to reach this gate: this one, and the
        record this gate answers for when it answers for another."""
        self.check_singleton()
        models_named = [self._name]
        if "res_model" in self._fields and self.res_model:
            models_named.append(self.res_model)
        return models_named

    def _contract_routes(self, routes_by_model: dict[str, list[str]]) -> list[str]:
        self.check_singleton()
        found: list[str] = []
        for model_name in self._contract_models():
            found.extend(routes_by_model.get(model_name, []))
        return sorted(dict.fromkeys(found))

    def _contract_scheme(self) -> str:
        self.check_singleton()
        lines = []
        if self.auth_type in _SCHEME_SENTENCES:
            lines.append(_SCHEME_SENTENCES[self.auth_type])
        elif self.auth_type.startswith("hmac_"):
            digest = self.auth_type.removeprefix("hmac_").upper()
            header = self.signature_header or "X-Hub-Signature-256"
            prefix = self.signature_prefix or ""
            lines.append(
                f"{header}: {prefix}<{digest} of the raw body under the shared secret>."
            )
        else:
            lines.append(f"Authentication: {self.auth_type}.")
        if self.timestamp_verification_enabled:
            lines.append(
                f"{self.timestamp_header or 'X-Webhook-Timestamp'}: the call's "
                f"own time, no older than {self.timestamp_max_age_seconds}s."
            )
        if self._inbound_auth_mode() == self.AUTH_MODE_AUDIT:
            lines.append(
                "This gate is in audit mode: a call that fails the check is "
                "admitted and recorded, not refused."
            )
        return "\n".join(lines)

    def _contract_limits(self) -> list[str]:
        self.check_singleton()
        limits = [f"Body at most {self._inbound_max_payload_size()} bytes."]
        if self.rate_limit_enabled and self.rate_limit_requests:
            window = self.rate_limit_window_seconds or 60
            limits.append(
                f"At most {self.rate_limit_requests} calls per {window}s; "
                "beyond that the call is refused, not queued."
            )
        allowed = [part.strip() for part in (self.ip_whitelist or "").split(",")]
        allowed = [part for part in allowed if part]
        if allowed:
            limits.append(f"Called from {', '.join(allowed)} only.")
        if "duplicate_detection_enabled" in self._fields and (
            self.duplicate_detection_enabled
        ):
            window = getattr(self, "duplicate_window_seconds", 0)
            limits.append(
                "A call repeated"
                + (f" inside {window}s" if window else "")
                + " is answered 409 and not processed twice."
            )
        return limits

    def _contract_last_call(self) -> str:
        self.check_singleton()
        if not self.id:
            return ""
        exchange = (
            self.env["integration.exchange"]
            .sudo()
            .search(
                [
                    ("channel_id", "=", f"{self._name},{self.id}"),
                    ("direction", "=", "inbound"),
                    ("request_payload", "!=", False),
                ],
                order="id desc",
                limit=1,
            )
        )
        if not exchange:
            return ""
        when = fields.Datetime.to_string(exchange.create_date)
        return f"{exchange.request_method or 'POST'} {when}\n{exchange.request_payload}"
