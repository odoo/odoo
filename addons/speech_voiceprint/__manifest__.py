{
    "name": "Speech - Voiceprints",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Employees",
    "summary": "Recognise employees by voice in transcribed calls and meetings",
    "description": """
Speech - Voiceprints
====================

Each employee records one phrase, once, with consent. The server turns it into a
speaker embedding -- a vector; the sample audio is discarded -- kept on
``speech.voiceprint``. When a recording is transcribed, every voice of its
transcript (``speech.speaker``) is embedded the same way and compared with the
company's voiceprints: a clear match names the voice's employee and their
contact, an unclear one leaves the voice for a person or for context.

Only employees are enrolled. Customers and suppliers are never identified by
voice.

Runs on the CPU with ``av`` for decoding, ``sherpa-onnx`` and a WeSpeaker ONNX
model under ``<data_dir>/models`` (``speech_voiceprint.model_path``); nothing
leaves the server. Without the libraries or the model the module installs and
leaves voices anonymous. ``speech_voiceprint.phrase`` sets the phrase read at
enrolment; ``.threshold`` and ``.margin`` how sure a match must be.
    """,
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "speech",
    ],
    "external_dependencies": {
        "python": [
            "numpy",
        ],
    },
    "data": [
        "security/ir.access.csv",
        "data/ir_config_parameter.xml",
        "views/speech_voiceprint_views.xml",
        "views/ir_attachment_views.xml",
        "views/speech_voiceprint_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "speech_voiceprint/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "speech_voiceprint/static/tests/**/*",
        ],
    },
}
