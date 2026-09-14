{
    "name": "Speech - AI Engines",
    "version": "19.0.1.1.0",
    "category": "Hidden",
    "sequence": 10,
    "summary": "Transcription and synthesis engines on the gateway_ml registry",
    "description": """
Speech - AI Engines
===================

The engines ``speech`` deliberately does not ship. Both are registered on the
document layer, so neither is reachable by name and neither is asked for
directly: a recording read at the ``EXPENSIVE`` ceiling reaches the reader, and
``speech``'s own ``_speech_synthesize`` reaches the writer. It does the reaching
rather than ``Document.of`` because a writer has no cost to be ordered by and no
fall-through, so the layer would hand the work to whichever engine registered
first, credential or not.

``ai_transcription``
    A reader of audio and video, yielding timed cues. It selects a model of kind
    ``audio`` through the gateway router, ``MlRouter`` -- by cost, accuracy or speed, filtered
    by which credentials this company actually holds -- and walks the model's
    fallback chain. Nothing here names a vendor, and adding one is an
    ``gateway.ml.model`` record rather than a code change.

``ai_speech``
    A writer per audio mimetype, consuming text and emitting sound, selecting a
    model of kind ``speech`` the same way. Registered per mimetype rather than
    once, because a writer states the one format it emits and the caller's
    choice of ``audio/mpeg`` or ``audio/wav`` has to reach the right one.

Both degrade the same way: with no credential for any audio model, selection
returns nothing, the reader answers with no cues and ``can_transcribe`` is
False, so the UI says the feature is unavailable instead of failing at a vendor
call.

``kind`` gains ``speech``
-------------------------
``gateway.ml.model.kind`` already separated chat, vision, audio and embeddings. Text to
speech is a fifth thing a model name decides, and it is added here rather than
in ``gateway_ml`` because the concept arrives with these engines.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "speech",
        "gateway_ml",
    ],
    "data": [
        "data/ai_models_data.xml",
    ],
    "auto_install": True,
}
