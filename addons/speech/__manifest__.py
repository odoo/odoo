{
    "name": "Speech",
    "version": "19.0.1.5.0",
    "category": "Hidden",
    "sequence": 10,
    "summary": "Transcription and synthesis for every stored recording",
    "description": """
Speech
======

Speech is a property of a binary, not of a conversation. Anything this database
stores as audio or video can be turned into words, and any words it holds can be
turned into audio. That is the whole of this module, and it deliberately knows
no channel: it is not about calls, not about voice messages and not about
documents. Those are consumers.

Reading speech
--------------
Transcription is registered as a reader of the document layer, at ``EXPENSIVE``,
exactly as local OCR is. One consequence follows from the cost alone and is not
written anywhere: a document is derived only up to the ceiling its caller sets,
so a recording is never transcribed by accident.

The cost ladder buys nothing else here yet, and the difference is worth stating
rather than assuming. A dearer reader does run only where every cheaper one
answered nothing, but at ``CUES`` the only reader claiming a container mimetype
is the engine: ``vtt`` and ``srt`` claim subtitle *files*, and nothing demuxes a
track out of an mp4 or a mkv. So a recording that already carries subtitles is
sent to an engine like any other. A demuxing reader below ``EXPENSIVE`` would
change that with no change here, which is the argument for the ladder -- not a
claim that it is already being used.

The transcript is therefore not a field this module invented. It is the
attachment's ``index_content`` -- the one place this database already puts "what
is inside this binary, in words" -- so a recording answers the ordinary
attachment search with no search code of its own, and every ``extract``
strategy that reads text starts working on recordings without being told that
audio exists. ``transcript_cues`` holds the same words with their timing, for
playback and for subtitles.

Writing speech
--------------
Synthesis is a writer of the same layer, consuming ``text`` and emitting audio,
so an engine is registered exactly as a reader is and no vendor is named here.

``_speech_synthesize`` does not go through ``Document.of``, and the reason is a
real difference between the two halves. A reader carries a cost and an empty
answer falls through to the next one, so a reader that cannot run costs nothing.
A writer carries neither: ``Document.of`` takes the first writer claiming the
mimetype, and cannot see that it holds no credential. So this picks the first
engine that reports itself usable and calls it. Two guards come with that: the
built-in text writer accepts any mimetype, so with no engine installed the call
would otherwise write a UTF-8 text file and label it audio; and with two engines
installed, the one without a key would otherwise answer.

Timelines
---------
Recordings are ``media`` timelines of ``media.segment``. Transcripts are not
segments: they live on the attachment they describe, which is why no flag
distinguishes a media artifact from a transcript and no transcript is excluded
from the overlap check.

This module extends ``mixin.media.timeline`` with the joined transcript, one
rolled-up state and three hooks, and ``media.segment`` with its attachment's
cues and state. The ``transcript_timeline`` widget is the ``media_timeline``
player with the words following along.

Live capture
------------
``mixin.media.live`` turns a timeline into one that fills while someone talks:
the client sends five-to-ten-second chunks, each becomes a ``live`` segment
transcribed by a high-priority job through the same engines, policy and
retention as any recording, and each chunk's words are pushed on the bus under
``speech.live``. The channel ``speech.live/<model>/<id>`` is served to whoever
may read the record. ``speech.dictation`` is the live timeline of one person
dictating into an editor -- its chunks are transcribed under
``speech.transcription.dictation`` and kept a week -- and
``static/src/live_capture`` holds the browser side: a recorder that cuts WAV
chunks at pauses and a session that sends them and hands back their words in
order.

Vocabulary
----------
``speech.vocabulary`` holds the brands, places and names a transcriber must spell
right, shared or per company. The first hundred, in order, travel with every
transcription as the engine's key terms. A module adds its own kinds of term.

No engine ships here
--------------------
This module registers no reader and no writer. ``speech_ai`` provides both on
the ``gateway_ml`` registry; ``speech_local`` reads on this server, for a
company no vendor may serve. With neither installed, ``can_transcribe`` is
False everywhere and the actions say so rather than failing at a vendor call.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "media",
        "bus",
    ],
    "data": [
        "security/ir.access.csv",
        "views/ir_attachment_views.xml",
        "views/media_segment_views.xml",
        "views/speech_vocabulary_views.xml",
        "views/speech_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "speech/static/src/**/*",
            (
                "remove",
                "speech/static/src/worklets/**/*",
            ),
        ],
        "web.assets_unit_tests": [
            "speech/static/tests/**/*",
        ],
    },
}
