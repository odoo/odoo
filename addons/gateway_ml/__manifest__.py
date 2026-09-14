{
    "name": "API AI",
    "version": "19.0.1.21.0",
    "category": "Hidden",
    "sequence": 10,
    "summary": "AI provider registry, orchestration and vendor clients",
    "description": """
API AI
======

AI layer on the outbound API transport.

Models
------
* ``gateway.ml.provider`` -- delegates to ``integration.service``; holds what the API
  key decides: reliability, free tier, fallback chain, and ``has_vision`` /
  ``has_audio`` rolled up from its models
* ``gateway.ml.model.fallback`` -- one ordered hop of a model's fallback chain
* ``gateway.ml.model`` -- holds what the model name decides: cost per token, context
  window, output cap, vision, function calling, accuracy and speed. A provider
  names one of its own as ``default_model_id``, and that is the model
  ``MlRouter`` ranks on and ``_resolve_model`` runs: cost and capability
  follow the model name, not the API key.
* ``ai.use.case.tag`` -- provider classification: vision, reasoning, speed,
  budget, long context, OCR, embeddings, audio

Provider operations
-------------------
A vendor's wire lives in rows, not in Python. ``gateway.ml.provider.service``
names, per operation (chat, transcribe, transcribe_timed, synthesize, embed),
the ``integration.service`` the call rides, the wire it speaks, the path, the
default model and the timeout -- Gemini's chat and audio ride two services.
The ``gateway.ml.model`` row carries what that model needs in a body:
``request_extra`` (DeepSeek's thinking switch, a reasoning effort),
``max_tokens_param`` -- OpenAI's reasoning models refuse ``max_tokens`` --
``min_max_tokens``, and whether sampling parameters are accepted. A caller's
own keyword still wins in ``OpenAICompatibleClient``, so a caller can turn
DeepSeek's thinking back on for one request.
``tools/wire_formats.py`` shapes and reads the wires: ``get_openai_content``
and ``get_anthropic_content`` build image-carrying messages,
``read_openai_content`` and ``read_anthropic_content`` are the single reader per
wire that both stacks use, and the Whisper form and readers sit beside them.
``strip_json_fence``, in ``tools/json_payload.py``, is the fence half of
``parse_json_response`` for callers that must not let it raise.

Routing
-------
* ``MlRouter.run(operation, MlRequest(...))`` is the call a consumer makes:
  ``chat`` (with ``images`` it needs a model that sees), ``transcribe``,
  ``transcribe_timed`` (with ``vocabulary`` and ``speakers``) or ``synthesize``.
  It selects the model, walks the fallback chain and dispatches to the wire's
  client, and returns an ``MlResult`` with ``text``, ``cues`` and their
  ``duration``, or ``audio``, and the model that answered. A ``provider``
  narrows selection to that vendor, preferring its default model. Callers no
  longer know which client class or method a vendor needs.
* ``MlRouter.select_model`` picks a ``gateway.ml.model`` of the ``kind`` the
  caller will call -- a kind is a method, so it is required -- by cost, accuracy,
  speed or balanced score, filtered by the model's own capability and by an
  unexpired credential for the current company. Cost is read in the unit the
  kind is priced in -- per minute for audio, a three-to-one blend of input and
  output for text -- and an unpriced model is scored at the candidates' median
  price rather than as free. A free tier breaks a tie on price; it does not
  outrank a cheaper model.
* ``run_with_fallback`` walks ``ai.model.fallback_ids`` in their sequence --
  ``gateway.ml.model.fallback`` rows, so the order is an administrator's, not the model
  list's. A hop may stay on one vendor -- a smaller model on a key already held --
  or cross to another; a hop that cannot answer for the model (an audio model
  behind a chat model) is refused when configured, and archived or keyless hops
  are skipped when run. A non-retryable failure is re-raised as itself. Nothing
  seeds a chain: acceptable degradation is a deployment's to state.
* The ``gateway.ml.model`` rows are the catalogue a client checks a model name and an
  output cap against; class constants only add to them.

Clients
-------
Two ways to reach a vendor, both on the generic HTTP transport, so both inherit
session pooling, retry, rate limiting, response caching, secret redaction and
the event log.

* ``tools/ai_clients/`` -- a class per wire, not per vendor:
  ``OpenAICompatibleClient``, ``ClaudeClient`` (Anthropic Messages),
  ``GeminiClient`` (the native wire) and ``DeepgramClient``, in
  ``WIRE_CLIENTS``. ``get_client_class`` reads a provider's operation on its own
  service -- chat first -- and ``get_ai_client`` binds that wire's class to the
  provider's service, so OpenAI, Groq, Moonshot and DeepSeek are one class on
  four services. Raising, credential resolved from the company. What
  ``MlRouter`` drives, through ``gateway.ml.provider._get_ai_client``.
* ``tools/provider_assistant.py`` -- ``ProviderAssistant``, one class driving
  any provider's chat and transcribe operations off its rows, built by
  ``gateway.ml.provider._assistant(model=)``. Fail-soft, and authenticated by
  the company's ``integration.connection`` like every other outbound call, so
  it is configured only when the company is connected to the operation's
  service. It is the only way to reach the ``gemini_openai`` endpoint, which
  Gemini's chat operation uses and which no class targets -- ``GeminiClient``
  is on ``gemini``, the native wire. ``tests/test_registry_coherence.py``
  requires every provider to resolve a wire client, so that ``_get_ai_client``
  can answer for whichever one the router selects. The Telegram bots'
  assistants are its callers;
  ``tools/assistant_adoption.py`` moved their own keys onto connections.

The Claude Agent SDK, which drives the Claude Code CLI as a subprocess rather
than calling a wire, is ``ai_project``'s, its only caller.

Audio
-----
``transcribe`` returns text; ``transcribe_cues`` returns the same words with the
moment each was said, which is what a player and a subtitle track need. Both
wires answer the same signature. OpenAI transcribes text on ``gpt-transcribe``,
which returns no timestamps, and asks ``whisper-1`` for ``verbose_json`` segments
when timing is wanted -- the ``transcribe_timed`` operation's model; Deepgram asks for utterances
and carries the speaker through where diarization gave it one. ``gateway.ml.model``
says which models time their words (``has_timestamps``): speech_ai selects on
it, and a fallback hop may not hand a timed request to a model without it.
OpenAI shuts ``whisper-1`` down on 2027-02-26 and names only untimed
replacements, so from then on OpenAI can no longer serve ``transcribe_cues``;
Deepgram and Groq still can.

``synthesize`` is the other direction: ``OutboundAPIClient.request`` takes
``raw=True`` and hands back the binary response, so Deepgram's ``/speak`` and the
OpenAI wire both speak. A vendor that writes no audio says so by carrying no
``synthesize`` operation rather than from a client. Deepgram's client keeps only
what a caller uses -- ``transcribe_file``, ``transcribe_cues`` and
``synthesize``; its URL, streaming and audio-intelligence helpers had no caller
outside their tests and are gone.

Depends on ``integration`` alone.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "integration",
    ],
    "data": [
        "security/api_ai_security.xml",
        "security/ir.model.access.csv",
        "data/ai_services_data.xml",
        "data/ai_use_case_tags_data.xml",
        "data/ai_providers_data.xml",
        "data/ai_models_data.xml",
        "data/ai_provider_services_data.xml",
        "views/ai_provider_views.xml",
        "views/ai_model_views.xml",
        "views/ai_use_case_tag_views.xml",
        "views/ai_menu.xml",
        "views/integration_exchange_views.xml",
        "views/res_company_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
}
