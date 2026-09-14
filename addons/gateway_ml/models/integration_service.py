from odoo import models
from odoo.tools import ormcache

from ..tools.usage import USAGE_READERS, usage_cost


class IntegrationService(models.Model):
    _inherit = "integration.service"

    def _exchange_usage_values(self, url, request_kwargs, response_body):
        values = super()._exchange_usage_values(url, request_kwargs, response_body)
        wire, provider_ids = self._ml_wire_and_providers(self.id)
        reader = USAGE_READERS.get(wire)
        usage = reader and reader(url, request_kwargs or {}, response_body)
        if not usage:
            return values
        values.update(
            {
                "ml_input_tokens": usage["input_tokens"],
                "ml_output_tokens": usage["output_tokens"],
                "ml_audio_seconds": usage["audio_seconds"],
            }
        )
        model = (
            self.env["gateway.ml.model"]
            .with_context(active_test=False)
            .search(
                [
                    ("code", "=", usage["model"]),
                    ("provider_id", "in", provider_ids),
                ],
                limit=1,
            )
        )
        if model:
            values.update(
                {"ml_model_id": model.id, "ml_cost": usage_cost(model, usage)}
            )
        return values

    @ormcache("service_id")
    def _ml_wire_and_providers(self, service_id):
        operations = (
            self.env["gateway.ml.provider.service"]
            .sudo()
            .search([("service_id", "=", service_id)])
        )
        return operations[:1].wire or None, tuple(operations.provider_id.ids)
