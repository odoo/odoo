import logging
import statistics
import time

from odoo import fields

from odoo.addons.integration.tools.api_client import OutboundAPIClient
from odoo.addons.integration.tools.exceptions import (
    AuthenticationError,
    ClientError,
    CommError,
    ValidationError,
)

_logger = logging.getLogger(__name__)

NON_RETRYABLE_ERRORS = (AuthenticationError, ClientError, ValidationError)

STRATEGIES = ("balanced", "cost", "accuracy", "speed")


def is_retryable(exc):
    return not isinstance(exc, NON_RETRYABLE_ERRORS)


def _as_list(value):
    return [value] if isinstance(value, str) else list(value)


class AIOrchestrator:
    _CALLER_ANNOTATIONS = ("origin_model", "origin_record_id")

    def __init__(self, env):
        self.env = env

    def select_model(
        self,
        kind,
        *,
        use_case_tags=None,
        required_capabilities=None,
        optimize_for="balanced",
        company_id=None,
        provider_code=None,
    ):
        if optimize_for not in STRATEGIES:
            raise ValueError(
                f"Unknown optimization strategy {optimize_for!r}; expected one of "
                f"{', '.join(STRATEGIES)}",
            )
        AIModel = self.env["gateway.ml.model"]
        domain = [
            ("kind", "in", _as_list(kind)),
            ("provider_id.active", "=", True),
        ]
        if provider_code is not None:
            domain.append(("provider_id.code", "in", _as_list(provider_code)))
        if use_case_tags:
            domain.append(
                ("provider_id.best_for_tag_ids.code", "in", list(use_case_tags))
            )
        if required_capabilities:
            unknown = set(required_capabilities) - set(AIModel._fields)
            if unknown:
                raise ValueError(
                    f"Unknown AI capability fields: {', '.join(sorted(unknown))}",
                )
            domain.extend(
                (field, "=", value) for field, value in required_capabilities.items()
            )

        candidates = AIModel.search(domain)
        usable_providers = self._get_usable_providers(
            candidates.provider_id, company_id
        )
        usable = candidates.filtered(lambda m: m.provider_id in usable_providers)
        if not usable:
            _logger.info(
                "No %s model is usable for company_id=%s (%s candidate(s) before "
                "the credential check; domain %s)",
                kind,
                company_id or self.env.company.id,
                len(candidates),
                domain,
            )
            return AIModel
        return self._rank(usable, optimize_for)[0]

    def execute_with_fallback(
        self,
        primary_model,
        request_func,
        fallback_chain=None,
        log_metadata=None,
        company_id=None,
    ):
        chain = self._get_runnable_chain(primary_model, fallback_chain, company_id)
        last_error = None
        previous_model = None

        for position, ai_model in enumerate(chain):
            provider = ai_model.provider_id
            annotated = provider.with_context(
                **{
                    OutboundAPIClient.EVENT_LOG_ANNOTATIONS_KEY: self._event_annotations(
                        ai_model, position > 0, previous_model, log_metadata
                    )
                }
            )
            _logger.debug(
                "AI request %s/%s: %s on %s",
                position + 1,
                len(chain),
                ai_model.code,
                provider.code,
            )
            started = time.monotonic()
            try:
                result = request_func(self._get_client(annotated, company_id), ai_model)
            except Exception as error:
                if not is_retryable(error):
                    _logger.warning(
                        "%s on %s failed with %s, which no other model can fix; "
                        "not trying the %s remaining hop(s): %s",
                        ai_model.code,
                        provider.code,
                        type(error).__name__,
                        len(chain) - position - 1,
                        error,
                    )
                    raise
                _logger.warning(
                    "%s on %s failed: %s", ai_model.code, provider.code, error
                )
                last_error = error
                previous_model = ai_model
                continue

            _logger.info(
                "AI request succeeded with %s on %s in %.0fms",
                ai_model.code,
                provider.code,
                (time.monotonic() - started) * 1000,
            )
            return result

        raise CommError(
            f"All {len(chain)} AI model(s) failed. Last error: {last_error}"
        ) from last_error

    def _get_runnable_chain(self, primary_model, fallback_chain, company_id):
        hops = (
            primary_model.fallback_model_ids
            if fallback_chain is None
            else self.env["gateway.ml.model"].union(*fallback_chain)
        )
        hops = hops.filtered(
            lambda m: (
                m.active and m != primary_model and m._can_stand_in_for(primary_model)
            )
        )
        usable_providers = self._get_usable_providers(hops.provider_id, company_id)
        skipped = hops.filtered(lambda m: m.provider_id not in usable_providers)
        if skipped:
            _logger.debug(
                "Fallback hop(s) %s have no usable credential and are skipped",
                skipped.mapped("code"),
            )
        return [primary_model, *(hops - skipped)]

    def _get_usable_providers(self, providers, company_id=None):
        company_id = company_id or self.env.company.id
        now = fields.Datetime.now()
        Credential = self.env["credential.credential"]
        keyless = providers.filtered(lambda p: p.auth_type == "none")
        credential_of = {
            provider: Credential._get_for_endpoint(
                provider.endpoint_id, company=company_id
            )
            for provider in providers - keyless
        }
        # One read for every credential; each came from its own search, so reading
        # the field record by record would issue one query per provider.
        Credential.union(*credential_of.values()).mapped("date_expiration")
        return keyless | self.env["gateway.ml.provider"].union(
            *(
                provider
                for provider, credential in credential_of.items()
                if credential
                and not (
                    credential.date_expiration and credential.date_expiration < now
                )
            )
        )

    def _rank(self, ai_models, strategy):
        priced = [cost for cost in (m._get_unit_cost() for m in ai_models) if cost]
        typical = statistics.median(priced) if priced else 1.0

        def cost_of(ai_model):
            return ai_model._get_unit_cost() or typical

        if strategy == "cost":
            return ai_models.sorted(
                lambda m: (cost_of(m), not m.provider_id.has_free_tier)
            )
        if strategy == "accuracy":
            return ai_models.sorted(lambda m: int(m.accuracy_rating), reverse=True)
        if strategy == "speed":
            return ai_models.sorted(lambda m: int(m.speed_rating), reverse=True)

        def balanced_score(ai_model):
            quality = (
                2 * int(ai_model.accuracy_rating)
                + int(ai_model.speed_rating)
                + int(ai_model.provider_id.reliability_rating)
            )
            return quality / max(0.1, cost_of(ai_model) / typical)

        return ai_models.sorted(balanced_score, reverse=True)

    def _get_client(self, provider, company_id=None):
        return provider._get_ai_client(company_id)

    def _event_annotations(self, ai_model, was_fallback, previous_model, metadata=None):
        metadata = metadata or {}
        tags = [
            f"ai_provider:{ai_model.provider_id.code}",
            f"ai_model:{ai_model.code}",
            f"fallback:{was_fallback}",
        ]
        if was_fallback and previous_model:
            tags.append(f"after:{previous_model.code}")
        tags.extend(
            f"{key}:{value}"
            for key, value in metadata.items()
            if value and key not in self._CALLER_ANNOTATIONS
        )

        annotations = {"tags": ",".join(tags)}
        for key in self._CALLER_ANNOTATIONS:
            if metadata.get(key):
                annotations[key] = metadata[key]
        return annotations


def get_ai_orchestrator(env):
    return AIOrchestrator(env)
