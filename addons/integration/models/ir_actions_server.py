import logging

from odoo import _, api, fields, models
from odoo.api import Environment
from odoo.exceptions import ValidationError
from odoo.libs import netguard
from odoo.modules.registry import Registry

from ..tools.api_client import get_api_client
from ..tools.exceptions import CommError

_logger = logging.getLogger(__name__)


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    webhook_endpoint_id = fields.Many2one(
        comodel_name="integration.service",
        string="Through Endpoint",
        ondelete="restrict",
        help="Send this webhook through a configured outbound endpoint, so it "
        "carries that endpoint's credential, is subject to its rate limit and is "
        "recorded in its event log. The webhook URL must be on the endpoint's host "
        "or listed in its Allowed Hosts. Leave empty to POST the URL directly with "
        "no authentication, which is what a webhook action does by default.",
    )

    @api.constrains("webhook_endpoint_id", "state")
    def _check_webhook_endpoint_is_for_a_webhook(self):
        for action in self:
            if action.webhook_endpoint_id and action.state != "webhook":
                raise ValidationError(
                    _(
                        "'%(name)s' is not a webhook action, so it has nothing "
                        "to send through an endpoint.",
                        name=action.name,
                    )
                )

    @api.constrains("webhook_endpoint_id")
    def _check_webhook_endpoint_does_not_retry(self):
        for action in self.filtered("webhook_endpoint_id"):
            if action.webhook_endpoint_id.retry_enabled:
                raise ValidationError(
                    _(
                        "Endpoint '%(endpoint)s' has retry enabled, which would "
                        "hold a worker through the backoff after the transaction "
                        "has already committed. Turn retry off on the endpoint, "
                        "or point '%(name)s' at one that does not retry.",
                        endpoint=action.webhook_endpoint_id.display_name,
                        name=action.name,
                    )
                )

    def _prepare_webhook_delivery(self, url, timeout, action_label, target):
        self.check_singleton()
        if not self.webhook_endpoint_id:
            return super()._prepare_webhook_delivery(url, timeout, action_label, target)

        return _EndpointDelivery(
            dbname=self.env.cr.dbname,
            endpoint_code=self.webhook_endpoint_id.code,
            company_id=self.env.company.id,
            uid=self.env.uid,
            url=url,
            timeout=timeout,
            action_label=action_label,
            target=target,
            policy=self.env["ir.egress"]._get_policy("public"),
        )


class _EndpointDelivery:
    def __init__(
        self,
        dbname,
        endpoint_code,
        company_id,
        uid,
        url,
        timeout,
        action_label,
        target,
        policy,
    ):
        self.dbname = dbname
        self.endpoint_code = endpoint_code
        self.company_id = company_id
        self.uid = uid
        self.url = url
        self.timeout = timeout
        self.action_label = action_label
        self.target = target
        self.policy = policy

    def __call__(self, json_values):
        _logger.debug(
            "Webhook %s to %s - start, through endpoint %s",
            self.action_label,
            self.target,
            self.endpoint_code,
        )
        try:
            netguard.check_url(self.url, policy=self.policy)
        except netguard.DestinationRefused as refusal:
            _logger.error(
                "Webhook %s to %s was NOT sent through endpoint %s: %s. The "
                "address was allowed when the action ran and is not any more -- "
                "the name resolved differently between the check and the send.",
                self.action_label,
                self.target,
                self.endpoint_code,
                refusal,
            )
            return
        try:
            registry = Registry(self.dbname)
            with registry.cursor() as cr:
                env = Environment(
                    cr, self.uid, {"allowed_company_ids": [self.company_id]}
                )
                client = get_api_client(
                    env, self.endpoint_code, self.company_id, egress_policy="public"
                )
                client.post(
                    self.url,
                    data=json_values,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout,
                )
                _logger.info(
                    "Webhook %s to %s - succeeded through %s",
                    self.action_label,
                    self.target,
                    self.endpoint_code,
                )
        except CommError as e:
            _logger.error(
                "Webhook %s to %s failed through endpoint %s and will NOT be "
                "retried: %s",
                self.action_label,
                self.target,
                self.endpoint_code,
                e,
            )
        except Exception:
            _logger.exception(
                "Webhook %s to %s could not be delivered through endpoint %s",
                self.action_label,
                self.target,
                self.endpoint_code,
            )
