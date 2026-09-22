from typing import Any

from odoo import api, models

_SCHEME_DEFINITIONS: dict[str, tuple[str, dict[str, Any]]] = {
    "bearer": (
        "receiverBearer",
        {
            "type": "http",
            "scheme": "bearer",
            "description": "The token the caller's receiver row holds, in "
            "Authorization: Bearer, or in X-Device-Token for a device that "
            "cannot set Authorization.",
        },
    ),
    "api_key": (
        "receiverApiKey",
        {
            "type": "http",
            "scheme": "bearer",
            "description": "The key the caller's receiver row holds, "
            "presented as a bearer token.",
        },
    ),
    "none": (
        "receiverOpen",
        {
            "type": "apiKey",
            "in": "header",
            "name": "X-Odoo-Receiver",
            "description": "This receiver admits its caller without a "
            "credential: the subject in the path, the address allow-list and "
            "the call budget are what gate it. No header is read.",
        },
    ),
    "subject": (
        "receiverSubject",
        {
            "type": "apiKey",
            "in": "path",
            "name": "subject",
            "description": "The caller is proven by what the path carries -- a "
            "signed token, an identifier the subject verifies itself -- and "
            "not by a credential of its own.",
        },
    ),
    "custom": (
        "receiverCustom",
        {
            "type": "apiKey",
            "in": "header",
            "name": "X-Odoo-Receiver",
            "description": "The receiver verifies the caller with a scheme of "
            "its own; read its row to see which.",
        },
    ),
}


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def _openapi_security_for(self, route) -> list[tuple[str, dict[str, Any]]] | None:
        routing = route.routing
        if routing.get("auth") != "receiver":
            return None
        receiver = routing.get("receiver")
        if not receiver:
            return []
        model_name = receiver.partition(":")[0]
        model = self.env.get(model_name)
        if model is None:
            return []
        if "auth_type" not in model._fields:
            # The subject proves the caller: a token in the path it checks
            # itself, or a Resolution's verifier. No header is read.
            return [_SCHEME_DEFINITIONS["subject"]]
        resolved: dict[str, dict[str, Any]] = {}
        for auth_type in self._openapi_receiver_auth_types(model_name):
            named = _SCHEME_DEFINITIONS.get(auth_type)
            if named is None:
                named = self._openapi_signature_scheme(model_name, auth_type)
            if named:
                resolved[named[0]] = named[1]
        return sorted(resolved.items())

    @api.model
    def _openapi_receiver_auth_types(self, model_name: str) -> list[str]:
        model = self.env.get(model_name)
        if model is None or "auth_type" not in model._fields:
            return []
        rows = model.sudo().with_context(active_test=False).search([])
        used = sorted({row.auth_type for row in rows if row.auth_type})
        if used:
            return used
        # No row answers for this door yet; what one would carry is the
        # field's own default, which is what a partner is told to send.
        default = model._fields["auth_type"].default
        default = default(model) if callable(default) else default
        return [default] if default else []

    @api.model
    def _openapi_signature_scheme(
        self, model_name: str, auth_type: str
    ) -> tuple[str, dict[str, Any]] | None:
        if not auth_type.startswith("hmac_"):
            return None
        model = self.env[model_name].sudo().with_context(active_test=False)
        headers = {
            row.signature_header
            for row in model.search([("auth_type", "=", auth_type)])
            if row.signature_header
        }
        header = min(headers) if len(headers) == 1 else "X-Hub-Signature-256"
        digest = auth_type.removeprefix("hmac_").upper()
        return (
            f"receiver{digest.title()}Signature",
            {
                "type": "apiKey",
                "in": "header",
                "name": header,
                "description": f"{digest} of the raw body under the secret the "
                "caller's receiver row holds, in this header; the row states "
                "its prefix and how long a signed timestamp stays valid.",
            },
        )
