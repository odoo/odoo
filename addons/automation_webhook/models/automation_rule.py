import logging
import traceback
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
        string="Log Calls",
        default=False,
    )

    auth_type = fields.Selection(
        string="Webhook Authentication",
        default="none",
        help="How incoming webhook calls are authenticated. HMAC/bearer read "
        "their secret from the linked credential.",
    )
    credential_id = fields.Many2one(
        string="Webhook Secret",
        help="Credential holding the shared secret / token used to verify calls.",
    )
    rate_limit_enabled = fields.Boolean(
        string="Rate Limit",
        default=False,
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
            "name": _("Webhook Logs"),
            "res_model": "ir.logging",
            "view_mode": "list,form",
            "domain": [("path", "=", f"automation({self.id})")],
        }

    def _check_webhook_request(self, headers, body, remote_addr):
        self.check_singleton()
        return self._check_inbound_request(headers, body=body, remote_addr=remote_addr)

    def _webhook_ip_allowed(self, remote_addr):
        return self.is_ip_allowed(remote_addr)

    def _webhook_rate_ok(self):
        return self.check_rate_limit()

    def _execute_webhook(self, payload):
        self.check_singleton()

        if self.trigger != "on_webhook":
            _logger.warning(
                "Webhook #%s refused: rule trigger is %r, not 'on_webhook'.",
                self.id,
                self.trigger,
            )
            raise exceptions.ValidationError(
                _("This automation rule is not a webhook."),
            )

        ir_logging_sudo = self.env["ir.logging"].sudo()

        msg = "Webhook #%s triggered with payload %s"
        msg_args = (self.id, payload)
        _logger.debug(msg, *msg_args)
        if self.log_webhook_calls:
            ir_logging_sudo.create(self._prepare_logging_values(message=msg % msg_args))

        record = self.env[self.model_name]
        if self.record_getter:
            try:
                record = safe_eval.safe_eval(
                    self.record_getter,
                    self._prepare_eval_context(payload=payload),
                )
            except Exception:
                msg = "Webhook #%s could not be triggered because the record_getter failed:\n%s"
                msg_args = (self.id, traceback.format_exc())
                _logger.warning(msg, *msg_args)
                if self.log_webhook_calls:
                    ir_logging_sudo.create(
                        self._prepare_logging_values(
                            message=msg % msg_args,
                            level="ERROR",
                        ),
                    )
                raise

        if not record.exists() and self.record_getter:
            msg = "Webhook #%s could not be triggered because no record to run it on was found."
            msg_args = (self.id,)
            _logger.warning(msg, *msg_args)
            if self.log_webhook_calls:
                ir_logging_sudo.create(
                    self._prepare_logging_values(message=msg % msg_args, level="ERROR"),
                )
            raise exceptions.ValidationError(
                _("No record to run the automation on was found."),
            )

        try:
            if record:
                return self.with_context(webhook_payload=payload)._process(record)
            return self._run_webhook_recordless(payload)
        except Exception:
            msg = "Webhook #%s failed with error:\n%s"
            msg_args = (self.id, traceback.format_exc())
            _logger.warning(msg, *msg_args)
            if self.log_webhook_calls:
                ir_logging_sudo.create(
                    self._prepare_logging_values(message=msg % msg_args, level="ERROR"),
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
