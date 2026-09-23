{
    "name": "Speech Tests",
    "version": "19.0.1.0.0",
    "category": "Hidden/Tests",
    "sequence": 9876,
    "summary": "Test models and suites for the speech layer",
    "description": """
Speech Tests
============

Recording owners with no business meaning, so ``mixin.media.timeline`` and the
transcription pipeline are tested against a consumer that exists only to be one.
The engines are stubbed at the document layer, which is the same seam the real
ones register on, so a suite proves the wiring without a key or a network call.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "speech",
        "mail_speech",
        "speech_ai",
        "speech_analysis",
    ],
    "data": [
        "security/ir.access.csv",
    ],
}
