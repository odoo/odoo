import json
import logging
import secrets
import time
import traceback
from datetime import timedelta
from uuid import uuid4

from odoo import _, api, exceptions, fields, models
from odoo.http import request
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


def get_webhook_request_payload():
    if not request:
        return None
    try:
        payload = request.get_json_data()
    except ValueError:
        payload = {**request.httprequest.args}
    return payload


class AutomationRule(models.Model):
    _name = "automation.rule"
    _inherit = ["automation.rule", "mixin.inbound.gate"]

    url = fields.Char(
        compute="_compute_url",
        help="Use this URL in the third-party app to call this webhook.",
    )
    webhook_uuid = fields.Char(
        string="Webhook UUID",
        default=lambda self: str(uuid4()),
        copy=False,
        readonly=True,
    )
    record_getter = fields.Char(
        help="This code will be run to find on which record the automation rule "
        "should be run. Leave empty to run the rule record-less (e.g. a "
        "create-from-payload webhook receiver) — a non-empty default here "
        "would assume a payload shape (a '_model'/'_id' pair) the sender may "
        "not actually use, silently breaking the record-less path unless "
        "cleared by hand."
    )
    log_webhook_calls = fields.Boolean(
        string="Store Payloads",
        default=False,
        help="Keep each call's body on its exchange row. Every call is recorded "
        "either way, with its status, caller, timing and error; this only decides "
        "whether what the sender posted is kept too.",
    )

    auth_type = fields.Selection(
        string="Webhook Authentication",
        default="hmac_sha256",
        help="How incoming webhook calls are authenticated. HMAC/bearer read "
        "their secret from the linked credential.",
    )
    credential_id = fields.Many2one(
        string="Webhook Secret",
        help="Credential holding the shared secret / token used to verify calls.",
    )
    rate_limit_enabled = fields.Boolean(
        string="Rate Limit",
        default=True,
    )
    webhook_enforce_from = fields.Datetime(
        string="Enforce Authentication From",
        copy=False,
        help="Until this moment a call that fails authentication is still run, and "
        "recorded as accepted unauthenticated. Set when a rule that used to "
        "authenticate nothing gained a secret, so its sender has time to start "
        "signing. Empty: authentication is enforced.",
    )
    rate_limit_requests = fields.Integer(
        string="Requests / Window",
        default=100,
        help="Token-bucket capacity (read by the rate-limit bucket).",
    )
    trigger = fields.Selection(
        selection_add=[("on_webhook", "On webhook"), ("on_write",)],
        ondelete={
            "on_webhook": lambda rules: rules.write(
                {"trigger": "on_hand", "active": False}
            )
        },
    )

    @api.depends("trigger", "webhook_uuid")
    def _compute_url(self):
        for automation in self:
            if automation.trigger != "on_webhook":
                automation.url = ""
            else:
                automation.url = (
                    f"{automation.get_base_url()}/web/hook/{automation.webhook_uuid}"
                )

    def action_rotate_webhook_uuid(self):
        for automation in self:
            automation.webhook_uuid = str(uuid4())

    def action_view_webhook_logs(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Webhook Calls"),
            "res_model": "integration.exchange",
            "view_mode": "list,form",
            "domain": [("channel_id", "=", f"{self._name},{self.id}")],
        }

    WEBHOOK_AUDIT_DAYS = 30
    _SECRET_AUTH_TYPES = ("bearer", "api_key", "hmac_sha256", "hmac_sha512")

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        rules._create_missing_webhook_credentials()
        return rules

    def write(self, vals):
        result = super().write(vals)
        if {"trigger", "auth_type"} & set(vals):
            self._create_missing_webhook_credentials()
        return result

    def _create_missing_webhook_credentials(self):
        """Create and attach credentials to secret-auth webhooks without one.

        Leave existing credentials, including inactive ones, unchanged. Without
        an encryption key, provision nothing. Return no value.
        """
        if not self.env["credential.credential"]._is_encryption_key_configured():
            return
        category = self.env.ref(
            "credential.credential_category_custom", raise_if_not_found=False
        )
        for rule in self.filtered(
            lambda rule: (
                rule.trigger == "on_webhook"
                and rule.auth_type in self._SECRET_AUTH_TYPES
                and not rule.credential_id
            )
        ):
            rule.credential_id = rule._create_webhook_credential(category)

    def _create_webhook_credential(self, category):
        """Create and return a credential record containing a random secret."""
        self.check_singleton()
        return (
            self.env["credential.credential"]
            .sudo()
            .create(
                {
                    "name": f"Webhook secret: {self.name} ({secrets.token_hex(4)})",
                    "category_id": category.id if category else False,
                    "credential_value": secrets.token_urlsafe(32),
                }
            )
        )

    def action_generate_webhook_secret(self):
        category = self.env.ref(
            "credential.credential_category_custom", raise_if_not_found=False
        )
        for rule in self:
            rule.credential_id = rule._create_webhook_credential(category)
        return True

    def _get_webhook_auth_mode(self):
        self.check_singleton()
        if (
            self.webhook_enforce_from
            and fields.Datetime.now() < self.webhook_enforce_from
        ):
            return self.AUTH_MODE_AUDIT
        return self.AUTH_MODE_ENFORCE

    def _start_webhook_audit_window(self):
        self.write(
            {
                "webhook_enforce_from": fields.Datetime.now()
                + timedelta(days=self.WEBHOOK_AUDIT_DAYS)
            }
        )

    def _check_webhook_request(self, headers, body, remote_addr):
        self.check_singleton()
        return self._check_inbound_request(
            headers,
            body=body,
            remote_addr=remote_addr,
            mode=self._get_webhook_auth_mode(),
        )

    def _webhook_ip_allowed(self, remote_addr):
        return self.is_ip_allowed(remote_addr)

    def _webhook_rate_ok(self):
        return self.check_rate_limit()

    def _execute_webhook(self, payload):
        self.check_singleton()
        started = time.monotonic()
        try:
            result = self._dispatch_webhook(payload)
        except Exception as error:
            self._record_webhook_exchange(payload, started, error=error)
            raise
        self._record_webhook_exchange(payload, started)
        return result

    def _record_webhook_exchange(self, payload, started, error=None):
        httprequest = request.httprequest if request else None
        body = None
        if self.log_webhook_calls and payload is not None:
            body = json.dumps(payload, default=str)
        self._record_inbound_exchange(
            method=httprequest.method if httprequest else "POST",
            path=f"/web/hook/{(self.webhook_uuid or '')[:8]}",
            body=body,
            status_code=500 if error else 200,
            error=f"{type(error).__name__}: {error}" if error else None,
            remote_addr=httprequest.remote_addr if httprequest else None,
            user_agent=httprequest.headers.get("User-Agent") if httprequest else None,
            duration_ms=(time.monotonic() - started) * 1000,
            event_type="webhook",
        )

    def _dispatch_webhook(self, payload):
        if self.trigger != "on_webhook":
            _logger.warning(
                "Webhook #%s refused: rule trigger is %r, not 'on_webhook'.",
                self.id,
                self.trigger,
            )
            raise exceptions.ValidationError(
                _("This automation rule is not a webhook."),
            )

        _logger.debug("Webhook #%s triggered with payload %s", self.id, payload)

        record = self.env[self.model_name]
        if self.record_getter:
            try:
                record = safe_eval.safe_eval(
                    self.record_getter,
                    self._prepare_eval_context(payload=payload),
                )
            except Exception:
                _logger.warning(
                    "Webhook #%s could not be triggered because the record_getter "
                    "failed:\n%s",
                    self.id,
                    traceback.format_exc(),
                )
                raise

        if not record.exists() and self.record_getter:
            _logger.warning(
                "Webhook #%s could not be triggered because no record to run it on "
                "was found.",
                self.id,
            )
            raise exceptions.ValidationError(
                _("No record to run the automation on was found."),
            )

        try:
            if record:
                return self.with_context(webhook_payload=payload)._process(record)
            return self._run_webhook_recordless(payload)
        except Exception:
            _logger.warning(
                "Webhook #%s failed with error:\n%s", self.id, traceback.format_exc()
            )
            raise

    def _run_webhook_recordless(self, payload):
        self.check_singleton()
        for action in self.sudo().action_server_ids._sorted_by_dependency():
            action.with_context(
                active_model=self.model_name,
                active_ids=[],
                active_id=False,
                webhook_payload=payload,
            ).run()
        return True

    def _prepare_eval_context(self, payload=None):
        eval_context = super()._prepare_eval_context()
        if payload is not None:
            eval_context["payload"] = payload
        return eval_context
