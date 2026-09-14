import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

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

OPERATION_KINDS = {
    "chat": ("chat",),
    "transcribe": ("audio",),
    "transcribe_timed": ("audio",),
    "synthesize": ("speech",),
}


@dataclass(frozen=True)
class MlRequest:
    prompt: str = ""
    images: tuple = ()
    temperature: float | None = None
    max_tokens: int | None = None
    audio: bytes = b""
    filename: str = ""
    mimetype: str = ""
    language: str | None = None
    vocabulary: tuple = ()
    speakers: bool = False
    text: str = ""
    voice: str | None = None


@dataclass(frozen=True)
class MlResult:
    model: Any
    text: str | None = None
    cues: list = field(default_factory=list)
    duration: float = 0.0
    audio: bytes | None = None


def is_retryable(exc):
    return not isinstance(exc, NON_RETRYABLE_ERRORS)


def _as_list(value):
    return [value] if isinstance(value, str) else list(value)


class MlRouter:
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
        preferred=None,
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
        if preferred and preferred in usable:
            return preferred
        return self._rank(usable, optimize_for)[0]

    def run(
        self,
        operation,
        request,
        *,
        model=None,
        provider=None,
        optimize_for="balanced",
        use_case_tags=None,
        company_id=None,
        log_metadata=None,
    ):
        if operation not in OPERATION_KINDS:
            raise ValueError(
                f"Unknown operation {operation!r}; expected one of "
                f"{', '.join(OPERATION_KINDS)}",
            )
        kinds, capabilities = self._selection_of(operation, request)
        model = model or self.select_model(
            kinds,
            required_capabilities=capabilities or None,
            use_case_tags=use_case_tags,
            optimize_for=optimize_for,
            company_id=company_id,
            provider_code=provider.code if provider else None,
            preferred=provider.default_model_id if provider else None,
        )
        if not model:
            raise CommError(
                f"No model is usable for {operation}"
                + (f" on {provider.code}" if provider else "")
                + f" in company {company_id or self.env.company.id}",
            )
        return self.run_with_fallback(
            model,
            lambda client, ai_model: MlResult(
                ai_model, **self._dispatch(operation, request, client, ai_model)
            ),
            log_metadata=log_metadata,
            company_id=company_id,
        )

    @staticmethod
    def _selection_of(operation, request):
        capabilities = {}
        kinds = OPERATION_KINDS[operation]
        if operation == "chat" and request.images:
            kinds = ("chat", "vision")
            capabilities["has_vision"] = True
        if operation == "transcribe_timed":
            capabilities["has_timestamps"] = True
        return kinds, capabilities

    @staticmethod
    def _dispatch(operation, request, client, ai_model):
        sampling = {
            key: value
            for key, value in (
                ("temperature", request.temperature),
                ("max_tokens", request.max_tokens),
            )
            if value is not None
        }
        if operation == "chat" and request.images:
            data, media_type = request.images[0]
            return {
                "text": client.vision_completion(
                    request.prompt,
                    data,
                    media_type=media_type,
                    model=ai_model.code,
                    **sampling,
                )
            }
        if operation == "chat":
            return {
                "text": client.simple_completion(
                    request.prompt, model=ai_model.code, **sampling
                )
            }
        audio = {
            "filename": request.filename or "audio",
            "mimetype": request.mimetype or None,
            "language": request.language,
            "prompt": request.prompt or None,
            "vocabulary": tuple(request.vocabulary),
            "model": ai_model.code,
        }
        if operation == "transcribe":
            return {"text": client.transcribe(request.audio, **audio)}
        if operation == "transcribe_timed":
            cues = client.transcribe_cues(
                request.audio, speakers=request.speakers, **audio
            )
            return {"cues": cues, "duration": getattr(cues, "duration", 0.0)}
        return {
            "audio": client.synthesize(
                request.text,
                voice=request.voice,
                mimetype=request.mimetype or "audio/mpeg",
                model=ai_model.code,
            )
        }

    def run_with_fallback(
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


def get_router(env):
    return MlRouter(env)
