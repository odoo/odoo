{
    "name": "Speech - Local Engine",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Transcribe recordings on this server when no vendor may serve",
    "description": """
Speech - Local Engine
=====================

A transcription reader of the document layer that runs on this server's CPU:
nothing leaves it. It registers at ``EXPENSIVE`` and defers to its peers there,
so it reads a recording only when every other engine answered nothing -- the
company's ``gateway_ml`` policy denies the ``speech.transcription`` purpose, no
vendor credential is held, or the vendor call failed. A company that denies
vendors still transcribes, and one that allows them keeps its vendor.

The recording is decoded to 16 kHz mono, cut into utterances by a voice
activity detector, and each utterance is recognised by Whisper through
``sherpa-onnx``. With a speaker segmentation and a speaker embedding model
beside them, each utterance is also given the voice that speaks most of it, as
``SPEAKER_n``, like every other engine.

Models live in one directory, ``<data_dir>/models/speech_local`` unless
``speech_local.model_dir`` names another, under fixed names:

- ``encoder.onnx``, ``decoder.onnx``, ``tokens.txt``: a Whisper export for
  sherpa-onnx (``sherpa-onnx-whisper-*``);
- ``vad.onnx``: Silero VAD;
- ``segmentation.onnx`` and ``embedding.onnx``, optional: a pyannote
  segmentation model and a speaker embedding model, for speakers.

Without the four required files the engine declares itself unavailable and
``can_transcribe`` reflects the other engines only.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "speech",
    ],
    "external_dependencies": {
        "python": [
            "av",
            "numpy",
            "sherpa_onnx",
        ],
    },
}
