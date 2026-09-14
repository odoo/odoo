from datetime import date

from odoo import fields, models
from odoo.tools import ormcache

from ..tools.usage import USAGE_READERS, SpendCapReached, usage_cost


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

    def _check_before_request(self, company_id):
        super()._check_before_request(company_id)
        wire, _provider_ids = self._ml_wire_and_providers(self.id)
        if not wire:
            return
        company = self.env["res.company"].browse(company_id or self.env.company.id)
        cap = company.gateway_ml_monthly_budget
        if not cap:
            return
        spent = company._gateway_ml_spend_this_month()
        if spent >= cap:
            raise SpendCapReached(
                self.env._(
                    "%(company)s has spent %(spent).2f USD of its %(cap).2f USD monthly "
                    "machine learning budget; %(service)s is not called again before "
                    "%(next_month)s.",
                    company=company.name,
                    spent=spent,
                    cap=cap,
                    service=self.name,
                    next_month=_first_of_next_month(),
                )
            )

    @ormcache("service_id")
    def _ml_wire_and_providers(self, service_id):
        operations = (
            self.env["gateway.ml.provider.service"]
            .sudo()
            .search([("service_id", "=", service_id)])
        )
        return operations[:1].wire or None, tuple(operations.provider_id.ids)


def _first_of_next_month():
    today = fields.Datetime.now().date()
    return date(today.year + (today.month == 12), today.month % 12 + 1, 1)
